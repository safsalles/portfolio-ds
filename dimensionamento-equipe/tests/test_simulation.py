import numpy as np
import pytest

from src.distributions import DistSpec, build_sampler
from src.erlang import agents_needed, service_level
from src.simulation import (
    SIM_TOLERANCE,
    SimResult,
    compare_with_erlang,
    simulate_custom,
    simulate_queue,
    simulate_trace,
)


def test_determinism():
    a = simulate_queue(200, 360, 22, 20, 5000, seed=7)
    b = simulate_queue(200, 360, 22, 20, 5000, seed=7)
    assert a == b and isinstance(a, SimResult)


def test_mm1_wait_probability():
    r = simulate_queue(30, 60, 1, 0, 50000, seed=1)
    assert r.prob_wait == pytest.approx(0.5, abs=0.02)


def test_matches_erlang_c():
    n = agents_needed(200, 360, 0.8, 20)
    r = compare_with_erlang(200, 360, n, 20)
    assert r["abs_diff"] <= 0.02
    assert r["sim_ci_low"] - 0.01 <= r["erlang"] <= r["sim_ci_high"] + 0.01


def test_zero_agents_rejected():
    with pytest.raises(ValueError):
        simulate_queue(200, 360, 0, 20, 1000, seed=1)


def test_lognormal_differs_when_cv_high():
    n = agents_needed(200, 360, 0.8, 20)
    exp = compare_with_erlang(200, 360, n, 20, service="exp")
    logn = compare_with_erlang(200, 360, n, 20, service="lognormal", cv=2.0)
    assert logn["abs_diff"] > exp["abs_diff"]



def _svc(mean=360.0):
    return build_sampler(DistSpec("expon", {"mean": mean}))


def test_custom_exp_reproduces_erlang():
    n = agents_needed(200, 360, 0.8, 20)
    levels = [simulate_custom(None, _svc(), 200, n, 20, 20000, 42 + i).service_level for i in range(20)]
    erl = service_level(200 * 360 / 3600, n, 360, 20)
    assert abs(float(np.mean(levels)) - erl) <= SIM_TOLERANCE


def test_custom_deterministic_with_seed():
    a = simulate_custom(None, _svc(), 200, 22, 20, 3000, 9)
    b = simulate_custom(None, _svc(), 200, 22, 20, 3000, 9)
    assert a == b


def test_deterministic_arrivals_wait_less_than_poisson():
    const_gaps = lambda rng, n: np.full(n, 3600 / 200)
    poisson = simulate_custom(None, _svc(), 200, 22, 20, 30000, 1)
    regular = simulate_custom(const_gaps, _svc(), 200, 22, 20, 30000, 1)
    assert regular.prob_wait < poisson.prob_wait


def test_trace_constant_service_exact():
    r = simulate_trace(np.array([0.0, 1.0, 2.0]), lambda rng, n: np.full(n, 10.0), agents=1, wait_s=0, seed=0)
    assert r.n_calls == 3
    assert r.avg_wait_s == pytest.approx(9.0)
    assert r.prob_wait == pytest.approx(2 / 3)
    assert r.service_level == pytest.approx(1 / 3)


def test_custom_zero_agents_rejected():
    with pytest.raises(ValueError):
        simulate_custom(None, _svc(), 200, 0, 20, 100, 1)


def test_unstable_terminates():
    r = simulate_custom(None, _svc(), 400, 20, 20, 2000, 1)  # tráfego 40 erlangs, 20 agentes
    assert isinstance(r, SimResult) and r.service_level < 0.5

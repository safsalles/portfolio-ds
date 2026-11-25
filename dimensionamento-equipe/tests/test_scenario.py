from pathlib import Path

import pytest

from src.distributions import DistSpec
from src.erlang import agents_needed
from src.scenario import SimScenario, load_scenario, run_scenario

ROOT = Path(__file__).resolve().parents[1]

BASE = (
    "name: t\ncalls_per_hour: 100\nagents: {agents}\nwait_seconds: 20\nsl_target: 0.8\n"
    "service: {service}\narrival: null\n"
)


def write(tmp_path, agents=10, service="{dist: expon, params: {mean: 360}}"):
    f = tmp_path / "c.yaml"
    f.write_text(BASE.format(agents=agents, service=service), encoding="utf-8")
    return f


def test_load_example():
    sc = load_scenario(ROOT / "config" / "cenario_exemplo.yaml")
    assert sc.agents == 10 and sc.service.dist == "lognormal" and sc.arrival is None


def test_invalid_agents_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_scenario(write(tmp_path, agents=0))


def test_unknown_distribution_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_scenario(write(tmp_path, service="{dist: poisson, params: {mean: 1}}"))


def test_bad_param_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_scenario(write(tmp_path, service="{dist: lognormal, params: {mean: 360, cv: -1}}"))


def test_missing_field_rejected(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text("name: t\nagents: 3\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_scenario(f)


def test_run_scenario_exp_matches_erlang():
    n = agents_needed(200, 360, 0.8, 20)
    sc = SimScenario("t", DistSpec("expon", {"mean": 360.0}), None, 200.0, n, 20, 0.8)
    r = run_scenario(sc)
    assert r["erlang"] is not None and r["stable"] is True
    assert abs(r["sim_mean"] - r["erlang"]) <= 0.02


def test_non_exponential_has_no_erlang():
    sc = SimScenario("t", DistSpec("lognormal", {"mean": 360.0, "cv": 1.0}), None, 200.0, 24, 20, 0.8)
    assert run_scenario(sc)["erlang"] is None


def test_unstable_scenario_flagged():
    sc = SimScenario("t", DistSpec("expon", {"mean": 360.0}), None, 400.0, 20, 20, 0.8)  # 40 erlangs
    r = run_scenario(sc, n_calls=2000, replicas=3)
    assert r["stable"] is False and r["erlang"] is not None


def test_run_scenario_reports_mean_wait_and_it_falls_with_more_agents():
    base = dict(name="t", service=DistSpec("expon", {"mean": 360.0}), arrival=None, calls_per_hour=200.0, wait_seconds=20, sl_target=0.8)
    few = run_scenario(SimScenario(agents=21, **base), n_calls=8000, replicas=3)
    many = run_scenario(SimScenario(agents=26, **base), n_calls=8000, replicas=3)
    assert few["wait_mean_s"] > many["wait_mean_s"] >= 0.0

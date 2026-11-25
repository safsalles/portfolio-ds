import math
import time

import numpy as np
import pytest

from src.distributions import DISTRIBUTIONS, DistSpec, build_sampler, describe, spec_pdf


def g(x):
    return math.gamma(x)


def weibull_mean_cv(shape, scale):
    m = scale * g(1 + 1 / shape)
    var = scale**2 * (g(1 + 2 / shape) - g(1 + 1 / shape) ** 2)
    return m, math.sqrt(var) / m


def tri_mean_cv(a, c, b):
    m = (a + b + c) / 3
    var = (a * a + b * b + c * c - a * b - a * c - b * c) / 18
    return m, math.sqrt(var) / m


def beta_mean_cv(low, high, a, b):
    span = high - low
    m = low + span * a / (a + b)
    var = span**2 * a * b / ((a + b) ** 2 * (a + b + 1))
    return m, math.sqrt(var) / m


CASES = [
    (DistSpec("expon", {"mean": 300.0}), 300.0, 1.0),
    (DistSpec("lognormal", {"mean": 300.0, "cv": 1.0}), 300.0, 1.0),
    (DistSpec("gamma", {"mean": 300.0, "cv": 0.7}), 300.0, 0.7),
    (DistSpec("weibull", {"shape": 1.5, "scale": 300.0}), *weibull_mean_cv(1.5, 300.0)),
    (DistSpec("erlang", {"k": 3, "mean": 300.0}), 300.0, 1 / math.sqrt(3)),
    (DistSpec("normal", {"mean": 300.0, "sd": 60.0}), 300.0, 0.2),
    (DistSpec("triangular", {"low": 60.0, "mode": 200.0, "high": 600.0}), *tri_mean_cv(60.0, 200.0, 600.0)),
    (DistSpec("uniform", {"low": 60.0, "high": 600.0}), 330.0, (540 / math.sqrt(12)) / 330.0),
    (DistSpec("beta", {"low": 60.0, "high": 600.0, "a": 2.0, "b": 5.0}), *beta_mean_cv(60.0, 600.0, 2.0, 5.0)),
]


def test_all_nine_distributions_listed():
    assert set(DISTRIBUTIONS) == {s.dist for s, _, _ in CASES}


@pytest.mark.parametrize("spec,mean,cv", CASES, ids=[c[0].dist for c in CASES])
def test_sampler_mean_cv(spec, mean, cv):
    d = describe(spec, n=400_000, seed=1)
    assert d["mean"] == pytest.approx(mean, rel=0.02)
    assert d["cv"] == pytest.approx(cv, rel=0.05)


def test_normal_truncated_positive_and_fast():
    t0 = time.time()
    x = build_sampler(DistSpec("normal", {"mean": 1.0, "sd": 5.0}))(np.random.default_rng(0), 10_000)
    assert (x > 0).all() and len(x) == 10_000
    assert time.time() - t0 < 2.0


def test_unknown_dist_rejected():
    with pytest.raises(ValueError):
        build_sampler(DistSpec("poisson", {"mean": 1.0}))


@pytest.mark.parametrize(
    "spec",
    [
        DistSpec("lognormal", {"mean": 300.0, "cv": 0.0}),
        DistSpec("uniform", {"low": 10.0, "high": 5.0}),
        DistSpec("weibull", {"shape": 0.0, "scale": 1.0}),
        DistSpec("gamma", {"mean": 300.0}),
        DistSpec("expon", {"mean": 300.0, "extra": 1.0}),
        DistSpec("expon", {"mean": -1.0}),
        DistSpec("erlang", {"k": 0, "mean": 300.0}),
        DistSpec("triangular", {"low": 1.0, "mode": 9.0, "high": 5.0}),
    ],
)
def test_bad_params_rejected(spec):
    with pytest.raises(ValueError):
        build_sampler(spec)


def test_sampler_deterministic_with_seed():
    s = build_sampler(DistSpec("gamma", {"mean": 300.0, "cv": 0.7}))
    a = s(np.random.default_rng(5), 100)
    b = s(np.random.default_rng(5), 100)
    assert (a == b).all()



@pytest.mark.parametrize("spec,mean,cv", CASES, ids=[c[0].dist for c in CASES])
def test_spec_pdf_integrates_to_one_and_matches_mean(spec, mean, cv):
    xs = np.linspace(1e-6, mean * 25, 400_000)
    dens = spec_pdf(spec)(xs)
    assert np.trapezoid(dens, xs) == pytest.approx(1.0, abs=0.02)
    assert np.trapezoid(xs * dens, xs) == pytest.approx(mean, rel=0.03)


def test_spec_pdf_rejects_bad_spec():
    with pytest.raises(ValueError):
        spec_pdf(DistSpec("poisson", {"mean": 1.0}))

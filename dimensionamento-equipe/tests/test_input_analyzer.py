import numpy as np
import pytest
from matplotlib.figure import Figure

from src.distributions import DistSpec, build_sampler
from src.input_analyzer import CANDIDATES, clean_values, fit_distributions, histogram_with_fits


def sample(spec, n=20_000, seed=3):
    return build_sampler(spec)(np.random.default_rng(seed), n)


@pytest.mark.parametrize(
    "spec,top",
    [
        (DistSpec("lognormal", {"mean": 300.0, "cv": 0.8}), 2),
        (DistSpec("gamma", {"mean": 300.0, "cv": 0.7}), 2),
        (DistSpec("expon", {"mean": 300.0}), 3),
        (DistSpec("weibull", {"shape": 1.5, "scale": 300.0}), 2),
    ],
    ids=["lognormal", "gamma", "expon", "weibull"],
)
def test_recovers_source_distribution(spec, top):
    fits = fit_distributions(sample(spec))
    assert spec.dist in [f.name for f in fits[:top]]


def test_ranking_sorted_by_aic_and_ranks():
    fits = fit_distributions(sample(DistSpec("lognormal", {"mean": 300.0, "cv": 0.8})))
    aics = [f.aic for f in fits]
    assert aics == sorted(aics)
    assert [f.rank for f in fits] == list(range(1, len(fits) + 1))
    assert {f.name for f in fits} <= set(CANDIDATES)


def test_ks_and_sq_error_ranges():
    fits = fit_distributions(sample(DistSpec("gamma", {"mean": 300.0, "cv": 0.7})))
    assert all(0.0 <= f.ks_stat <= 1.0 and 0.0 <= f.ks_p <= 1.0 and f.sq_error >= 0.0 for f in fits)


def test_clean_values_counts():
    kept, rep = clean_values([1, "2,5", "", "abc", -3, 0, None, float("nan"), 7])
    assert list(kept) == [1.0, 2.5, 7.0]
    assert rep == {"kept": 3, "dropped_empty": 3, "dropped_non_numeric": 1, "dropped_nonpositive": 2}


def test_too_few_points_error():
    with pytest.raises(ValueError, match="pontos"):
        fit_distributions(np.arange(1, 10) + 0.5)


def test_constant_sample_error():
    with pytest.raises(ValueError, match="variância"):
        fit_distributions(np.full(500, 12.0))


def test_huge_outliers_do_not_crash():
    x = sample(DistSpec("lognormal", {"mean": 300.0, "cv": 0.8}), n=5000)
    x = np.append(x, 1e9)
    assert len(fit_distributions(x)) >= 1


def test_histogram_figure_returns_figure():
    x = sample(DistSpec("gamma", {"mean": 300.0, "cv": 0.7}), n=3000)
    fits = fit_distributions(x)
    fig = histogram_with_fits(x, fits[:3])
    assert isinstance(fig, Figure) and len(fig.axes) >= 1

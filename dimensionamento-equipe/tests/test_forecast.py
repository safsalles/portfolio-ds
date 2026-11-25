from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.forecast import (
    baseline_same_hour_4w,
    build_features,
    evaluate,
    evaluate_walk_forward,
    fit_poisson,
    mape,
    mape_details,
    predict,
    wape,
)

TZ = "America/New_York"


def make_series(seed=0, scale=1.0):
    idx = pd.date_range("2022-01-01", "2023-12-31 23:00", freq="h", tz="UTC")
    f = build_features(idx, TZ)
    work = (f["hour"].between(9, 17)).astype(float)
    weekday = (f["dow"] < 5).astype(float)
    rate = scale * (100 + 300 * work * (0.4 + 0.6 * weekday))
    rng = np.random.default_rng(seed)
    return pd.Series(rng.poisson(rate), index=idx, name="calls")


def test_baseline_exact_on_periodic_series():
    idx = pd.date_range("2023-01-02", periods=24 * 7 * 6, freq="h", tz="UTC")
    week = np.arange(24 * 7) % 50 + 1
    s = pd.Series(np.tile(week, 6), index=idx)
    b = baseline_same_hour_4w(s)
    assert b.iloc[: 24 * 7 * 4].isna().all()
    assert (b.iloc[24 * 7 * 4 :] == s.iloc[24 * 7 * 4 :]).all()


def test_metrics():
    a = pd.Series([10.0, 10.0])
    p = pd.Series([8.0, 12.0])
    assert wape(a, p) == pytest.approx(0.2)
    m, ignored = mape_details(pd.Series([10.0, 0.0]), pd.Series([8.0, 5.0]))
    assert m == pytest.approx(0.2) and ignored == 1
    assert mape(pd.Series([10.0, 0.0]), pd.Series([8.0, 5.0])) == pytest.approx(0.2)


def test_model_recovers_hourly_pattern():
    r = evaluate(make_series(), 2022, 2023)
    assert r["wape_model"] < 0.10
    assert r["wape_model"] < r["wape_baseline"]


def test_no_leakage():
    s = make_series()
    s2 = s.copy()
    in_test = s2.index.tz_convert(TZ).year == 2023
    s2[in_test] = s2[in_test] * 3
    a, b = evaluate(s, 2022, 2023), evaluate(s2, 2022, 2023)
    assert np.allclose(a["model"].result.params, b["model"].result.params)
    assert a["wape_model"] != b["wape_model"]


def test_same_metric_for_both():
    r = evaluate(make_series(), 2022, 2023)
    for k in ("wape_model", "wape_baseline", "mape_model", "mape_baseline", "n_hours", "gain_wape_rel"):
        assert k in r
    assert r["n_hours"] == 365 * 24 or r["n_hours"] > 8700


def test_holiday_feature():
    idx = pd.date_range("2023-07-03 12:00", periods=48, freq="h", tz="UTC")
    f = build_features(idx, TZ, holidays={date(2023, 7, 4)})
    local = idx.tz_convert(TZ)
    expected = np.array([d == date(2023, 7, 4) for d in local.date]).astype(int)
    assert (f["holiday"].to_numpy() == expected).all()


def test_walk_forward_has_same_keys_and_refits():
    s = make_series()
    s = s[s.index < pd.Timestamp("2023-04-01", tz="UTC")]
    r = evaluate_walk_forward(s, 2022, 2023)
    for k in ("wape_model", "wape_baseline", "mape_model", "n_hours", "gain_wape_rel", "forecast"):
        assert k in r
    assert r["refits"] == 3  # jan, fev, mar de 2023


def test_walk_forward_no_leakage_from_future_months():
    s = make_series()
    s = s[s.index < pd.Timestamp("2023-04-01", tz="UTC")]
    s2 = s.copy()
    feb = (s2.index.tz_convert(TZ).year == 2023) & (s2.index.tz_convert(TZ).month == 2)
    s2[feb] = s2[feb] * 3
    a, b = evaluate_walk_forward(s, 2022, 2023), evaluate_walk_forward(s2, 2022, 2023)
    fa, fb = a["forecast"], b["forecast"]
    local_month = fa.index.tz_convert(TZ).month
    upto_feb = local_month <= 2   # previsão de jan e fev só usa dados antes de cada mês
    assert np.allclose(fa[upto_feb], fb[upto_feb])
    assert not np.allclose(fa[~upto_feb], fb[~upto_feb])  # março enxerga o fevereiro alterado


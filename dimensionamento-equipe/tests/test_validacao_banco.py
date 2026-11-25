import numpy as np
import pandas as pd
import pytest

from src.distributions import DistSpec, build_sampler
from src.simulation import queue_waits
from src.validacao_banco import replay_validation

SVC = DistSpec("lognormal", {"mean": 120.0, "cv": 1.0})


def synthetic_calls(n_days=140, cph=120.0, agents=5, hang_share=0.0, seed=11):
    """Traço sintético gerado por um modelo conhecido (M/lognormal/5), 10h às 11h."""
    rng = np.random.default_rng(seed)
    sampler = build_sampler(SVC)
    rows = []
    for d, date in enumerate(pd.date_range("2024-01-01", periods=n_days)):
        gaps = rng.exponential(3600 / cph, 400)
        arr = 10 * 3600 + np.cumsum(gaps)
        arr = arr[arr < 11 * 3600]
        svc = sampler(rng, len(arr))
        waits = queue_waits(arr, svc, agents)
        for a, s, w in zip(arr, svc, waits):
            hung = rng.random() < hang_share
            rows.append((date, a, "PS", "HANG" if hung else "AGENT", w, 0.0 if hung else s))
    return pd.DataFrame(rows, columns=["date", "entry_s", "type", "outcome", "q_time_s", "ser_time_s"])


def test_self_consistency():
    calls = synthetic_calls()
    r = replay_validation(calls, build_sampler(SVC), agents=5, wait_s=20, day_type="weekday", hours=(10, 11), seed=5)
    assert r["real_mean_wait_s"] > 0
    assert abs(r["sim_mean_wait_s"] - r["real_mean_wait_s"]) / r["real_mean_wait_s"] < 0.10
    assert abs(r["sim_service_level"] - r["real_service_level"]) < 0.03


def test_reports_abandoned_share():
    calls = synthetic_calls(n_days=60, hang_share=0.2)
    r = replay_validation(calls, build_sampler(SVC), agents=5, wait_s=20, day_type="weekday", hours=(10, 11))
    win = calls[calls["date"].dt.day_of_week.isin([6, 0, 1, 2, 3])]
    expected = (win["outcome"] == "HANG").mean()
    assert r["abandoned_share"] == pytest.approx(expected, abs=1e-9)


def test_empty_window_error():
    calls = synthetic_calls(n_days=10)
    with pytest.raises(ValueError, match="sem ligações"):
        replay_validation(calls, build_sampler(SVC), agents=5, wait_s=20, day_type="weekday", hours=(3, 4))


def test_bad_day_type_error():
    with pytest.raises(ValueError):
        replay_validation(synthetic_calls(n_days=5), build_sampler(SVC), 5, 20, "feriado", (10, 11))


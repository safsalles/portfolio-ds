import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analisar_entradas import (  # noqa: E402
    analisar_atendimento,
    analisar_valores,
    exportar_nyc_horario,
    intervalos_chegada,
    intervalos_por_faixa,
)
from src.distributions import DistSpec, build_sampler  # noqa: E402


def test_intervalos_ties_do_not_vanish():
    ts = pd.Series(pd.to_datetime(["2024-01-01 10:00:05"] * 4 + ["2024-01-01 10:00:06"] * 3))
    iv = intervalos_chegada(ts)
    assert len(iv) == 6 and (iv > 0).all()


def test_intervalos_mean_close_to_true():
    rng = np.random.default_rng(0)
    arrivals_s = np.cumsum(rng.exponential(20.0, 20000))  # taxa conhecida: 1 a cada 20 s
    ts = pd.Series(pd.Timestamp("2024-01-01") + pd.to_timedelta(np.floor(arrivals_s), unit="s"))  # resolução de 1 s
    assert intervalos_chegada(ts).mean() == pytest.approx(20.0, rel=0.02)


def test_intervalos_por_faixa_does_not_cross_days():
    ts = pd.Series(pd.to_datetime(
        ["2024-01-02 10:00:05", "2024-01-02 10:00:15", "2024-01-03 10:00:05", "2024-01-03 10:00:25",
         "2024-01-02 23:00:00"]))
    iv = intervalos_por_faixa(ts, (10, 11), weekdays_only=False)
    assert len(iv) == 2  # um intervalo por dia; nada atravessa a noite nem entra fora da faixa


def test_intervalos_por_faixa_weekdays_only():
    # 2024-01-06 é sábado
    ts = pd.Series(pd.to_datetime(["2024-01-06 10:00:05", "2024-01-06 10:00:15", "2024-01-08 10:00:05", "2024-01-08 10:00:15"]))
    assert len(intervalos_por_faixa(ts, (10, 11), weekdays_only=True)) == 1
    assert len(intervalos_por_faixa(ts, (10, 11), weekdays_only=False)) == 2


def test_analisar_valores_ranking_and_proposal():
    x = build_sampler(DistSpec("lognormal", {"mean": 300.0, "cv": 0.8}))(np.random.default_rng(1), 30000)
    r = analisar_valores(x, max_points=10000)
    assert r["n_total"] == 30000 and r["n_usado"] == 10000
    assert [row["rank"] for row in r["ranking"]] == list(range(1, len(r["ranking"]) + 1))
    assert r["proposta"]["dist"] == r["ranking"][0]["name"]
    assert "lognormal" in [row["name"] for row in r["ranking"][:2]]


def test_analisar_valores_is_deterministic():
    x = build_sampler(DistSpec("gamma", {"mean": 300.0, "cv": 0.7}))(np.random.default_rng(2), 5000)
    assert analisar_valores(x, max_points=2000) == analisar_valores(x, max_points=2000)


def test_analisar_atendimento_uses_served_positive_only():
    svc = build_sampler(DistSpec("lognormal", {"mean": 120.0, "cv": 1.0}))(np.random.default_rng(3), 4000)
    calls = pd.DataFrame({
        "date": pd.Timestamp("1999-01-01"), "entry_s": 0, "type": "PS",
        "outcome": ["AGENT"] * 4000 + ["HANG"] * 500,
        "q_time_s": 0, "ser_time_s": np.concatenate([np.round(svc).astype(int) + 1, np.zeros(500, int)]),
    })
    r = analisar_atendimento(calls, max_points=100000)
    assert r["n_total"] == 4000


def test_exportar_nyc_horario_roundtrip(tmp_path):
    src = tmp_path / "h.parquet"
    pd.DataFrame({"hour_ts": pd.date_range("2024-01-01", periods=5, freq="h"), "calls": [1, 2, 3, 4, 5]}).to_parquet(src)
    out = tmp_path / "h.csv.gz"
    exportar_nyc_horario(src, out)
    back = pd.read_csv(out)
    assert list(back.columns) == ["hour_ts", "calls"] and list(back["calls"]) == [1, 2, 3, 4, 5]


def test_varrer_agentes_waits_never_increase_with_more_agents():
    sys.path.insert(0, str(ROOT / "tests"))
    from test_validacao_banco import SVC, synthetic_calls

    from analisar_entradas import mais_proximo, varrer_agentes

    calls = synthetic_calls(n_days=40)
    rows = varrer_agentes(calls, build_sampler(SVC), [4, 5, 6, 8, 10], wait_s=20, day_type="weekday", hours=(10, 11))
    assert [r["agentes"] for r in rows] == [4, 5, 6, 8, 10]
    waits = [r["sim_mean_wait_s"] for r in rows]
    assert all(b <= a + 1e-9 for a, b in zip(waits, waits[1:]))
    best = mais_proximo(rows, waits[2])
    assert best == 6

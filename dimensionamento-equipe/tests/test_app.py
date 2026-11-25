import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import logic  # noqa: E402
from src.distributions import DistSpec  # noqa: E402


def csv_bytes(n=300, decimal=",", header="tempo"):
    x = np.random.default_rng(0).lognormal(5.0, 0.7, n)
    body = "\n".join(f"{v:.2f}".replace(".", decimal) for v in x)
    return f"{header}\n{body}\n".encode("utf-8")


def test_load_defaults_without_raw_or_results_parquet(tmp_path):
    (tmp_path / "results").mkdir()
    (tmp_path / "data" / "exemplos").mkdir(parents=True)
    (tmp_path / "results" / "results.json").write_bytes((ROOT / "results" / "results.json").read_bytes())
    for f in (ROOT / "data" / "exemplos").iterdir():
        (tmp_path / "data" / "exemplos" / f.name).write_bytes(f.read_bytes())
    d = logic.load_defaults(tmp_path)
    assert d["proposal"].dist and len(d["fits"]) >= 5
    assert d["calls_per_hour"] > 0 and d["agents"] >= 1
    assert "Technion" in d["source_note"] and "NYC 311" in d["source_note"]


def test_analyze_upload_valid_csv_with_decimal_comma():
    r = logic.analyze_upload(csv_bytes(), None)
    assert "error" not in r and len(r["fits"]) >= 1
    assert r["report"]["kept"] == 300


@pytest.mark.parametrize(
    "payload,column",
    [
        (b"", None),
        (b"abc\ndef\nghi\n", None),
        (csv_bytes(), "coluna_que_nao_existe"),
        (b"tempo\n" + b"10\n" * 100, None),  # todos iguais
        (b"tempo\n1\n2\n3\n", None),          # poucos pontos
        (b"\xff\xfe\x00garbage", None),       # binário
    ],
    ids=["vazio", "texto", "coluna", "constante", "poucos", "binario"],
)
def test_analyze_upload_invalid_returns_error(payload, column):
    r = logic.analyze_upload(payload, column)
    assert "error" in r and isinstance(r["error"], str)


def test_simulate_caps_n_calls(monkeypatch):
    monkeypatch.setattr(logic, "MAX_CALLS", 3000)
    r = logic.simulate(DistSpec("expon", {"mean": 300.0}), None, 100.0, 10, 20, 0.8, n_calls=10_000_000)
    assert r["capped"] is True and 0.0 <= r["sim_mean"] <= 1.0


def test_simulate_unstable_flag():
    r = logic.simulate(DistSpec("expon", {"mean": 300.0}), None, 400.0, 10, 20, 0.8, n_calls=2000)
    assert r["stable"] is False and "warning" in r


def test_app_runs_without_upload():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "app.py"), default_timeout=120).run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Fontes misturadas" in text or "Mixed sources" in text
    assert "weibull" in " ".join(str(df.value) for df in at.dataframe).lower() or "weibull" in text.lower()


def test_sweep_agents_monotone_and_min_for_target():
    svc = DistSpec("expon", {"mean": 300.0})
    df = logic.sweep_agents(svc, None, 100.0, 20, 0.8, [5, 10, 12, 15, 20])
    assert list(df["agents"]) == [5, 10, 12, 15, 20]
    sl = list(df["service_level"])
    assert all(b >= a - 0.02 for a, b in zip(sl, sl[1:]))
    assert df.loc[df["agents"] == 5, "stable"].item() is False
    n = logic.min_agents_for_target(df, 0.8)
    assert n is not None and df.loc[df["agents"] == n, "service_level"].item() >= 0.8
    assert logic.min_agents_for_target(df, 0.9999999) in (None, 20)


def test_sweep_agents_rejects_bad_range():
    with pytest.raises(ValueError):
        logic.sweep_agents(DistSpec("expon", {"mean": 300.0}), None, 100.0, 20, 0.8, [])


def test_app_validation_text_does_not_blame_empty_positions():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "app.py"), default_timeout=180).run()
    text = " ".join([w.value for w in at.warning] + [c.value for c in at.caption])
    assert "posições estavam ocupadas" not in text and "atendentes ativos" not in text
    assert "fila vazia" in text and "não está demonstrado" in text

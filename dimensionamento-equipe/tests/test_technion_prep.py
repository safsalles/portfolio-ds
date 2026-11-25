import gzip
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from preparar_technion import parse_technion, prepare  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "technion_amostra.txt"
RAW = ROOT / "data" / "raw" / "technion"
COLS = ["date", "entry_s", "type", "outcome", "q_time_s", "ser_time_s"]


def sample():
    return parse_technion(FIXTURE.read_text(encoding="utf-8").splitlines())


def test_parse_columns_and_values():
    df = sample()
    assert list(df.columns) == COLS and len(df) == 6
    first = df.iloc[0]
    assert first["date"] == pd.Timestamp("1999-01-01")
    assert (first["entry_s"], first["type"], first["outcome"], first["q_time_s"], first["ser_time_s"]) == (31, "PS", "HANG", 153, 0)


def test_parse_served_has_positive_service():
    df = sample()
    served = df[df["outcome"] == "AGENT"]
    assert len(served) == 2 and (served["ser_time_s"] > 0).all()
    assert list(served["ser_time_s"]) == [54, 114]


def test_abandoned_has_zero_service():
    df = sample()
    assert (df[df["outcome"] == "HANG"]["ser_time_s"] == 0).all()


def test_parse_space_separated_line():
    df = sample()
    assert df.iloc[-1]["type"] == "TT" and df.iloc[-1]["date"] == pd.Timestamp("1999-08-30")
    assert df.attrs["malformed"] == 0


def test_parse_counts_malformed():
    lines = FIXTURE.read_text(encoding="utf-8").splitlines() + ["lixo sem campos", "", "AA 1 2"]
    df = parse_technion(lines)
    assert len(df) == 6 and df.attrs["malformed"] == 2


@pytest.mark.skipif(not (RAW / "January1999.txt").exists(), reason="base bruta do Technion não baixada")
def test_prepare_counts_match_files(tmp_path):
    expected_rows = 0
    for f in RAW.glob("*.txt"):
        expected_rows += sum(1 for ln in f.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()) - 1  # menos o cabeçalho
    out = tmp_path / "technion.csv.gz"
    stats = prepare(RAW, out)
    assert stats["files"] == 12
    assert stats["calls"] + stats["malformed"] == expected_rows
    assert stats["served"] + stats["abandoned"] + stats["phantom"] == stats["calls"]
    assert stats["period"] == ["1999-01-01", "1999-12-31"]
    back = pd.read_csv(out, parse_dates=["date"])
    assert list(back.columns) == COLS and len(back) == stats["calls"]

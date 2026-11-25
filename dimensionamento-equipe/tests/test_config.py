from pathlib import Path

import pytest

from src.config import load_premissas

CFG = Path(__file__).resolve().parents[1] / "config" / "premissas.yaml"


def test_load_premissas_values():
    p = load_premissas(CFG)
    assert p.aht_seconds == 360
    assert p.shrinkage == 0.30
    got = [(s.name, s.sl_target, s.wait_seconds) for s in p.scenarios]
    assert got == [("80/20", 0.80, 20), ("90/30", 0.90, 30)]


@pytest.mark.parametrize("bad", [1.0, -0.1])
def test_invalid_shrinkage_rejected(tmp_path, bad):
    f = tmp_path / "p.yaml"
    f.write_text(
        f"aht_seconds: 360\nshrinkage: {bad}\nalert_threshold: 0.3\n"
        "train_year: 0\ntest_year: 0\nscenarios:\n  - {name: a, sl_target: 0.8, wait_seconds: 20}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_premissas(f)

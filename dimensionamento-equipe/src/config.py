"""Carregamento e validação das premissas (fictícias) do cenário."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Scenario:
    name: str
    sl_target: float
    wait_seconds: int


@dataclass(frozen=True)
class Premissas:
    aht_seconds: int
    shrinkage: float
    scenarios: tuple[Scenario, ...]
    alert_threshold: float
    train_year: int
    test_year: int


def load_premissas(path: str | Path) -> Premissas:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    shrinkage = float(raw["shrinkage"])
    if not 0.0 <= shrinkage < 1.0:
        raise ValueError(f"shrinkage deve estar em [0, 1): {shrinkage}")
    scenarios = []
    for s in raw["scenarios"]:
        target = float(s["sl_target"])
        if not 0.0 < target <= 1.0:
            raise ValueError(f"meta de serviço deve estar em (0, 1]: {target}")
        scenarios.append(Scenario(str(s["name"]), target, int(s["wait_seconds"])))
    return Premissas(
        aht_seconds=int(raw["aht_seconds"]),
        shrinkage=shrinkage,
        scenarios=tuple(scenarios),
        alert_threshold=float(raw.get("alert_threshold", 0.30)),
        train_year=int(raw.get("train_year", 0)),
        test_year=int(raw.get("test_year", 0)),
    )

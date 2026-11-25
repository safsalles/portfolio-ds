"""Cenário do usuário em YAML: distribuições, agentes e meta de serviço."""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from .distributions import DistSpec, build_sampler, describe
from .erlang import service_level
from .simulation import simulate_custom


@dataclass(frozen=True)
class SimScenario:
    name: str
    service: DistSpec
    arrival: DistSpec | None  # intervalo entre chegadas (s); None = Poisson pela taxa
    calls_per_hour: float
    agents: int
    wait_seconds: int
    sl_target: float


def _spec(raw, field_name: str) -> DistSpec:
    if not isinstance(raw, dict) or "dist" not in raw or "params" not in raw:
        raise ValueError(f"{field_name}: use {{dist: nome, params: {{...}}}}")
    spec = DistSpec(str(raw["dist"]), dict(raw["params"]))
    build_sampler(spec)  # valida nome, parâmetros e domínio
    return spec


def load_scenario(path: str | Path) -> SimScenario:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("arquivo de cenário vazio ou inválido")
    for k in ("name", "calls_per_hour", "agents", "wait_seconds", "sl_target", "service"):
        if k not in raw:
            raise ValueError(f"campo obrigatório ausente: {k}")
    agents = int(raw["agents"])
    if agents < 1:
        raise ValueError("agents deve ser >= 1")
    cph = float(raw["calls_per_hour"])
    if cph <= 0:
        raise ValueError("calls_per_hour deve ser > 0")
    wait = int(raw["wait_seconds"])
    target = float(raw["sl_target"])
    if wait < 0 or not 0 < target <= 1:
        raise ValueError("wait_seconds >= 0 e sl_target em (0, 1]")
    arrival = raw.get("arrival")
    return SimScenario(
        name=str(raw["name"]),
        service=_spec(raw["service"], "service"),
        arrival=_spec(arrival, "arrival") if arrival else None,
        calls_per_hour=cph,
        agents=agents,
        wait_seconds=wait,
        sl_target=target,
    )


def traffic_erlangs(sc: SimScenario) -> float:
    """Carga em erlangs = taxa de chegada x tempo médio de atendimento."""
    mean_service = describe(sc.service, n=100_000)["mean"]
    rate_per_s = 1.0 / describe(sc.arrival, n=100_000)["mean"] if sc.arrival else sc.calls_per_hour / 3600.0
    return rate_per_s * mean_service


def run_scenario(sc: SimScenario, n_calls: int = 20000, replicas: int = 20, seed: int = 42) -> dict:
    load = traffic_erlangs(sc)
    rate = (1.0 / describe(sc.arrival, n=100_000)["mean"] * 3600.0) if sc.arrival else sc.calls_per_hour
    svc = build_sampler(sc.service)
    arr = build_sampler(sc.arrival) if sc.arrival else None
    runs = [simulate_custom(arr, svc, rate, sc.agents, sc.wait_seconds, n_calls, seed + i) for i in range(replicas)]
    levels = np.array([r.service_level for r in runs])
    mean = float(levels.mean())
    half = 1.96 * float(levels.std(ddof=1)) / math.sqrt(replicas) if replicas > 1 else 0.0
    exp_poisson = sc.service.dist == "expon" and sc.arrival is None
    erlang = service_level(load, sc.agents, sc.service.params["mean"], sc.wait_seconds) if exp_poisson else None
    return {
        "sim_mean": mean,
        "wait_mean_s": float(np.mean([r.avg_wait_s for r in runs])),
        "sim_ci_low": mean - half,
        "sim_ci_high": mean + half,
        "erlang": erlang,
        "stable": bool(load < sc.agents),
        "traffic_erlangs": load,
    }


if __name__ == "__main__":
    scenario = load_scenario(sys.argv[1])
    print(scenario.name, run_scenario(scenario))


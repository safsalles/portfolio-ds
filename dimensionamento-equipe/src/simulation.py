"""Simulação de filas por eventos discretos (fila FIFO, M/M/c ou M/G/c)."""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

import numpy as np

from .erlang import service_level

WARMUP_FRACTION = 0.10
SIM_TOLERANCE = 0.02  # tolerância declarada entre simulação e Erlang C


@dataclass(frozen=True)
class SimResult:
    service_level: float
    prob_wait: float
    avg_wait_s: float
    n_calls: int


def _service_times(rng, n, aht_s, service, cv):
    if service == "exp":
        return rng.exponential(aht_s, n)
    if service == "lognormal":
        sigma2 = math.log(1.0 + cv**2)
        return rng.lognormal(math.log(aht_s) - sigma2 / 2.0, math.sqrt(sigma2), n)
    raise ValueError(f"service desconhecido: {service}")


def queue_waits(arrivals: np.ndarray, services: np.ndarray, agents: int) -> np.ndarray:
    """Espera de cada chamada numa fila FIFO com `agents` servidores (chegadas em ordem)."""
    free = [0.0] * agents
    heapq.heapify(free)
    waits = np.empty(len(arrivals))
    for i in range(len(arrivals)):
        start = max(arrivals[i], heapq.heappop(free))
        waits[i] = start - arrivals[i]
        heapq.heappush(free, start + services[i])
    return waits


def _run(arrivals: np.ndarray, services: np.ndarray, agents: int, wait_s: float, warmup: float) -> SimResult:
    """Fila FIFO com `agents` servidores; descarta a fração `warmup` inicial das chamadas."""
    n = len(arrivals)
    waits = queue_waits(arrivals, services, agents)[int(n * warmup):]
    return SimResult(
        service_level=float(np.mean(waits <= wait_s)),
        prob_wait=float(np.mean(waits > 1e-9)),
        avg_wait_s=float(np.mean(waits)),
        n_calls=len(waits),
    )


def simulate_custom(
    arrival_sampler,
    service_sampler,
    calls_per_hour: float,
    agents: int,
    wait_s: float,
    n_calls: int,
    seed: int,
) -> SimResult:
    """Simulação com amostradores escolhidos. arrival_sampler=None = chegadas de Poisson."""
    if agents < 1:
        raise ValueError("agents deve ser >= 1")
    rng = np.random.default_rng(seed)
    if arrival_sampler is None:
        gaps = rng.exponential(3600.0 / calls_per_hour, n_calls)
    else:
        gaps = arrival_sampler(rng, n_calls)
    arrivals = np.cumsum(gaps)
    services = service_sampler(rng, n_calls)
    return _run(arrivals, services, agents, wait_s, WARMUP_FRACTION)


def simulate_trace(arrival_times_s: np.ndarray, service_sampler, agents: int, wait_s: float, seed: int) -> SimResult:
    """Repete chegadas reais (em segundos); sem descarte de aquecimento."""
    if agents < 1:
        raise ValueError("agents deve ser >= 1")
    arrivals = np.sort(np.asarray(arrival_times_s, dtype=float))
    services = service_sampler(np.random.default_rng(seed), len(arrivals))
    return _run(arrivals, services, agents, wait_s, 0.0)


def simulate_queue(
    calls_per_hour: float,
    aht_s: float,
    agents: int,
    wait_s: float,
    n_calls: int,
    seed: int,
    service: str = "exp",
    cv: float = 1.0,
) -> SimResult:
    return simulate_custom(
        None,
        lambda rng, n: _service_times(rng, n, aht_s, service, cv),
        calls_per_hour,
        agents,
        wait_s,
        n_calls,
        seed,
    )

def compare_with_erlang(
    calls_per_hour: float,
    aht_s: float,
    agents: int,
    wait_s: float,
    replicas: int = 20,
    n_calls: int = 20000,
    seed: int = 42,
    service: str = "exp",
    cv: float = 1.0,
) -> dict:
    levels = np.array(
        [
            simulate_queue(calls_per_hour, aht_s, agents, wait_s, n_calls, seed + i, service, cv).service_level
            for i in range(replicas)
        ]
    )
    mean = float(levels.mean())
    half = 1.96 * float(levels.std(ddof=1)) / math.sqrt(replicas)
    erlang = service_level(calls_per_hour * aht_s / 3600.0, agents, aht_s, wait_s)
    return {
        "sim_mean": mean,
        "sim_ci_low": mean - half,
        "sim_ci_high": mean + half,
        "erlang": erlang,
        "abs_diff": abs(mean - erlang),
    }



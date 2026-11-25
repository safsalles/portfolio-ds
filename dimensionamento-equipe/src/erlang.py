"""Erlang C: probabilidade de espera, nível de serviço e agentes necessários.

Usa a recorrência do Erlang B (sem fatoriais), estável para tráfego alto.
"""
from __future__ import annotations

import math


def _erlang_b(traffic: float, agents: int) -> float:
    b = 1.0
    for k in range(1, agents + 1):
        b = traffic * b / (k + traffic * b)
    return b


def erlang_c(traffic: float, agents: int) -> float:
    """Probabilidade de a chamada esperar. traffic em erlangs."""
    if traffic <= 0:
        return 0.0
    if agents <= traffic:
        return 1.0
    b = _erlang_b(traffic, agents)
    return b / (1.0 - (traffic / agents) * (1.0 - b))


def service_level(traffic: float, agents: int, aht_s: float, wait_s: float) -> float:
    """Fração atendida em até wait_s segundos."""
    if traffic <= 0:
        return 1.0
    if agents <= traffic:
        return 0.0
    c = erlang_c(traffic, agents)
    return 1.0 - c * math.exp(-(agents - traffic) * wait_s / aht_s)


def average_speed_of_answer(traffic: float, agents: int, aht_s: float) -> float:
    if traffic <= 0:
        return 0.0
    if agents <= traffic:
        return math.inf
    return erlang_c(traffic, agents) * aht_s / (agents - traffic)


def agents_needed(
    calls_per_hour: float,
    aht_s: float,
    sl_target: float,
    wait_s: float,
    shrinkage: float = 0.0,
) -> int:
    """Menor número de agentes presentes que atinge a meta; com folga, escalados."""
    traffic = calls_per_hour * aht_s / 3600.0
    if traffic <= 0:
        return 0
    n = int(math.floor(traffic)) + 1
    while service_level(traffic, n, aht_s, wait_s) < sl_target:
        n += 1
    return math.ceil(n / (1.0 - shrinkage)) if shrinkage else n

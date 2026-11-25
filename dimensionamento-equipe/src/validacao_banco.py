"""Validação: repete as chegadas reais do banco (Technion) e compara com a espera real.

Ressalva importante: no banco real parte dos clientes desiste (HANG); o simulador não
modela abandono. Só as ligações atendidas entram como chegadas, e a fração de
abandono da faixa é reportada junto. A diferença é reportada como saiu, sem ajuste.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .simulation import simulate_trace

# Documentação do banco: semana de trabalho Domingo a Quinta; fim de semana Sexta e Sábado.
DAY_TYPES = {"weekday": {6, 0, 1, 2, 3}, "weekend": {4, 5}}  # pandas: segunda=0 ... domingo=6


def replay_validation(
    calls: pd.DataFrame,
    service_sampler,
    agents: int,
    wait_s: float,
    day_type: str,
    hours: tuple[int, int],
    seed: int = 0,
) -> dict:
    if day_type not in DAY_TYPES:
        raise ValueError(f"day_type deve ser um de {sorted(DAY_TYPES)}")
    h0, h1 = hours
    win = calls[
        calls["date"].dt.day_of_week.isin(DAY_TYPES[day_type])
        & (calls["entry_s"] >= h0 * 3600)
        & (calls["entry_s"] < h1 * 3600)
        & calls["outcome"].isin(["AGENT", "HANG"])
    ]
    served = win[win["outcome"] == "AGENT"]
    if served.empty:
        raise ValueError(f"sem ligações atendidas na faixa {day_type} {h0}h-{h1}h")

    sim_waits = []
    for k, (_, day) in enumerate(served.groupby("date")):
        arrivals = day["entry_s"].to_numpy(dtype=float)
        r = simulate_trace(arrivals, service_sampler, agents, wait_s, seed + k)
        # agrega por dia, ponderando pelo número de chamadas
        sim_waits.append((r.avg_wait_s, r.service_level, r.n_calls))
    n = sum(c for _, _, c in sim_waits)
    sim_mean = sum(a * c for a, _, c in sim_waits) / n
    sim_sl = sum(s * c for _, s, c in sim_waits) / n
    real_wait = served["q_time_s"].to_numpy(dtype=float)
    return {
        "n_calls": int(len(served)),
        "n_days": int(served["date"].nunique()),
        "real_mean_wait_s": float(real_wait.mean()),
        "sim_mean_wait_s": float(sim_mean),
        "real_service_level": float(np.mean(real_wait <= wait_s)),
        "sim_service_level": float(sim_sl),
        "abandoned_share": float((win["outcome"] == "HANG").mean()),
    }


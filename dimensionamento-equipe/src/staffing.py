"""Plano de pessoas por hora e por cenário de meta de serviço."""
from __future__ import annotations

import math

import pandas as pd

from .config import Premissas
from .erlang import agents_needed


def staffing_plan(forecast: pd.Series, premissas: Premissas) -> pd.DataFrame:
    rows = []
    for hour, calls in forecast.items():
        cph = math.ceil(calls) if calls > 0 else 0  # arredonda só para o cálculo
        for sc in premissas.scenarios:
            present = agents_needed(cph, premissas.aht_seconds, sc.sl_target, sc.wait_seconds)
            scheduled = math.ceil(present / (1.0 - premissas.shrinkage)) if present else 0
            rows.append(
                {
                    "hour": hour,
                    "scenario": sc.name,
                    "calls": float(calls),
                    "agents_present": present,
                    "agents_scheduled": scheduled,
                }
            )
    return pd.DataFrame(rows)


def scenario_cost(plan: pd.DataFrame) -> pd.DataFrame:
    g = plan.groupby("scenario", sort=False)
    return pd.DataFrame(
        {
            "agent_hours_present": g["agents_present"].sum(),
            "agent_hours_scheduled": g["agents_scheduled"].sum(),
            "peak_present": g["agents_present"].max(),
            "peak_scheduled": g["agents_scheduled"].max(),
        }
    ).reset_index()

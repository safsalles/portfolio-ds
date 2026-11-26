"""Gera site/index.html: a história do projeto em gráficos, num único arquivo sem dependências.

Todos os números vêm dos resultados do projeto. Precisa dos parquets de results/
(gerados por scripts/run_all.py). Uso: python scripts/gerar_pagina.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMPLATE = ROOT / "scripts" / "pagina_template.html"
OUT = ROOT / "site" / "index.html"
TZ = "America/New_York"
WEEK = ("2025-06-02", "2025-06-08")  # mesma semana das figuras do README
TARGET, WAIT = 0.80, 20


def build_data() -> dict:
    from app import logic
    from src.forecast import baseline_same_hour_4w

    res = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))
    nyc = pd.read_csv(ROOT / "data" / "exemplos" / "nyc311_horario.csv.gz", parse_dates=["hour_ts"])
    series = pd.Series(nyc["calls"].to_numpy(), index=pd.DatetimeIndex(nyc["hour_ts"]).tz_localize("UTC"))
    local = series.index.tz_convert(TZ)
    heat = series.groupby([local.day_of_week, local.hour]).mean().unstack()

    cmp_ = pd.read_parquet(ROOT / "results" / "previsto_realizado.parquet").set_index("hour")
    cmp_.index = cmp_.index.tz_convert(TZ)
    week = cmp_.loc[WEEK[0]:WEEK[1]]
    base = baseline_same_hour_4w(series).tz_convert(TZ).reindex(week.index)

    plan = pd.read_parquet(ROOT / "results" / "plano_pessoas.parquet")
    when = plan["hour"].dt.tz_convert(TZ)
    wd = plan[when.dt.day_of_week < 5]
    by_hour = wd.groupby(["scenario", when[wd.index].dt.hour])["agents_scheduled"].mean()

    d = logic.load_defaults(ROOT)
    agents = int(d["agents"])
    sweep = logic.sweep_agents(
        d["proposal"], None, d["calls_per_hour"], WAIT, TARGET, range(agents - 5, agents + 7)
    )

    f = res["forecast"]
    inv = res["investigacao"]
    return {
        "chegadas": {"media": [[round(float(v), 2) for v in heat.loc[i]] for i in range(7)],
                     "total": res["data"]["total_calls"]},
        "previsao": {
            "inicio": WEEK[0],
            "real": [int(v) for v in week["actual"]],
            "modelo": [round(float(v), 2) for v in week["forecast"]],
            "regra": [round(float(v), 2) for v in base],
            "erros": {"regra": f["reajuste_mensal"]["wape_baseline"], "unico": f["ajuste_unico"]["wape_model"],
                      "modelo": f["reajuste_mensal"]["wape_model"]},
        },
        "equipe": {
            "por_hora": {s: [round(float(by_hour[s][h]), 2) for h in range(24)] for s in by_hour.index.levels[0]},
            "custo": {s["scenario"]: s["agent_hours_scheduled"] for s in res["staffing"]},
        },
        "varredura": {
            "atual": agents, "chamadas_hora": d["calls_per_hour"], "meta": TARGET, "espera_s": WAIT,
            "linhas": json.loads(sweep.to_json(orient="records")),
        },
        "banco": {"cenarios": inv["cenarios"], "hora": inv["hora"], "ligacoes": inv["ligacoes_janela"]},
    }


def render(data: dict) -> str:
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("__DADOS__", blob)


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(build_data()), encoding="utf-8")
    print("OK", OUT, f"{OUT.stat().st_size / 1024:.0f} KB")

"""Executa o projeto inteiro e grava results/results.json.

Todo número do README e do notebook vem desse arquivo.
Uso: python scripts/run_all.py [--skip-spark]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_premissas  # noqa: E402
from src.forecast import evaluate, evaluate_walk_forward  # noqa: E402
from src.monitor import compare_intraday, find_alerts, run_monitor  # noqa: E402
from src.simulation import SIM_TOLERANCE, compare_with_erlang  # noqa: E402
from src.staffing import scenario_cost, staffing_plan  # noqa: E402

RAW = ROOT / "data" / "raw" / "nyc311_phone.csv"
HOURLY = ROOT / "data" / "processed" / "hourly.parquet"
OUT = ROOT / "results" / "results.json"
LOGNORMAL_CV = 1.5
TZ = "America/New_York"


def load_series() -> pd.Series:
    df = pd.read_parquet(HOURLY)
    idx = pd.DatetimeIndex(df["hour_ts"])
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    return pd.Series(df["calls"].to_numpy(), index=idx, name="calls").sort_index()


def pick_hours(forecast: pd.Series) -> dict[str, pd.Timestamp]:
    nz = forecast[forecast >= 5]
    peak = nz.idxmax()
    median = (nz - nz.median()).abs().idxmin()
    valley = (nz - nz.quantile(0.10)).abs().idxmin()
    return {"pico": peak, "mediana": median, "vale": valley}


def main(skip_spark: bool) -> None:
    prem = load_premissas(ROOT / "config" / "premissas.yaml")
    data_stats: dict = {}
    if not skip_spark:
        from src.pipeline import build_spark, run_pipeline

        HOURLY.parent.mkdir(parents=True, exist_ok=True)
        data_stats = run_pipeline(
            str(RAW),
            str(HOURLY),
            f"{prem.train_year}-01-01 00:00:00",
            f"{prem.test_year}-12-31 23:59:59",
            spark=build_spark("wfm-run"),
        )
        (ROOT / "results" / "data_stats.json").write_text(json.dumps(data_stats), encoding="utf-8")
    else:
        data_stats = json.loads((ROOT / "results" / "data_stats.json").read_text(encoding="utf-8"))

    series = load_series()
    ev_single = evaluate(series, prem.train_year, prem.test_year, tz=TZ)
    ev_single.pop("forecast"), ev_single.pop("model")
    # Operação realista: modelo reajustado todo mês só com dados passados.
    ev = evaluate_walk_forward(series, prem.train_year, prem.test_year, tz=TZ)
    forecast = ev.pop("forecast")

    plan = staffing_plan(forecast, prem)
    cost = scenario_cost(plan)

    sims = []
    for label, hour in pick_hours(forecast).items():
        calls = float(forecast[hour])
        for sc in prem.scenarios:
            row = plan[(plan["hour"] == hour) & (plan["scenario"] == sc.name)].iloc[0]
            n = int(row["agents_present"])
            common = dict(calls_per_hour=calls, aht_s=prem.aht_seconds, agents=n, wait_s=sc.wait_seconds)
            exp = compare_with_erlang(**common, service="exp")
            logn = compare_with_erlang(**common, service="lognormal", cv=LOGNORMAL_CV)
            sims.append(
                {
                    "hora": label,
                    "instante_utc": str(hour),
                    "chamadas_hora_prevista": round(calls, 1),
                    "cenario": sc.name,
                    "agentes_presentes": n,
                    "erlang": exp["erlang"],
                    "sim_exp": exp["sim_mean"],
                    "sim_exp_ic": [exp["sim_ci_low"], exp["sim_ci_high"]],
                    "diff_exp": exp["abs_diff"],
                    "sim_lognormal": logn["sim_mean"],
                    "diff_lognormal": logn["abs_diff"],
                }
            )

    actual = series.reindex(forecast.index)
    cmp = compare_intraday(forecast, actual)
    alerts = find_alerts(cmp, prem.alert_threshold)
    worst_day = alerts["hour"].dt.tz_convert(TZ).dt.date.value_counts().idxmax() if len(alerts) else None
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    day_mask = cmp["hour"].dt.tz_convert(TZ).dt.date == worst_day if worst_day else None
    replay = (
        run_monitor(
            forecast[forecast.index.isin(cmp.loc[day_mask, "hour"])],
            actual[actual.index.isin(cmp.loc[day_mask, "hour"])],
            prem.alert_threshold,
            webhook,
        )
        if worst_day
        else {"alerts": 0, "sent": 0}
    )

    results = {
        "data": {
            "fonte": "NYC 311 Service Requests (NYC Open Data), canal PHONE",
            "treino": prem.train_year,
            "teste": prem.test_year,
            **{k: int(v) for k, v in data_stats.items()},
            "horas_na_serie": int(len(series)),
            "chamadas_na_serie": int(series.sum()),
        },
        "forecast": {
            "ajuste_unico": {k: (float(v) if not isinstance(v, int) else v) for k, v in ev_single.items()},
            "reajuste_mensal": {k: (float(v) if not isinstance(v, int) else v) for k, v in ev.items()},
        },
        "staffing": json.loads(cost.to_json(orient="records")),
        "simulation": {"tolerancia": SIM_TOLERANCE, "cv_lognormal": LOGNORMAL_CV, "casos": sims},
        "monitor": {
            "limite_desvio": prem.alert_threshold,
            "horas_comparadas": int(len(cmp)),
            "horas_em_alerta": int(len(alerts)),
            "dia_com_mais_alertas": str(worst_day),
            "replay_dia": replay,
            "webhook_configurado": bool(webhook),
        },
        "premissas_ficticias": {
            "aht_seconds": prem.aht_seconds,
            "shrinkage": prem.shrinkage,
            "cenarios": [[s.name, s.sl_target, s.wait_seconds] for s in prem.scenarios],
        },
    }
    OUT.parent.mkdir(exist_ok=True)
    if OUT.exists():  # preserva o que scripts/analisar_entradas.py gravou
        prev = json.loads(OUT.read_text(encoding="utf-8"))
        results.update({k: prev[k] for k in ("analisador", "validacao_banco", "investigacao") if k in prev})
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    plan.to_parquet(ROOT / "results" / "plano_pessoas.parquet", index=False)
    cmp.to_parquet(ROOT / "results" / "previsto_realizado.parquet", index=False)
    print("OK", OUT)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-spark", action="store_true")
    main(ap.parse_args().skip_spark)




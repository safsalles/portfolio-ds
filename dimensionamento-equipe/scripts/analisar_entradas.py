"""Analisador de entradas: ajusta distribuições aos dados reais e grava results/results.json.

- Atendimento: tempos reais do Technion (data/exemplos/technion_chamadas.csv.gz).
- Chegadas: intervalos entre chamadas do NYC 311 por faixa de hora (precisa de
  data/raw/nyc311_phone.csv; sem ele, mantém o resultado já gravado em results.json).
- Validação: repete as chegadas reais do banco e compara a espera simulada com a real.

Uso: python scripts/analisar_entradas.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.distributions import DistSpec, build_sampler  # noqa: E402
from src.input_analyzer import clean_values, fit_distributions  # noqa: E402
from src.validacao_banco import replay_validation  # noqa: E402

EXEMPLOS = ROOT / "data" / "exemplos"
RESULTS = ROOT / "results" / "results.json"
NYC_RAW = ROOT / "data" / "raw" / "nyc311_phone.csv"
MAX_POINTS = 100_000  # amostra (aleatória, semente fixa) usada no ajuste, por velocidade
BANDS = {"0-6h": (0, 6), "9-17h": (9, 17), "18-24h": (18, 24)}
BANK_AGENTS = 8  # posições de atendimento segundo a documentação do banco
WAIT_S = 20


def intervalos_chegada(timestamps: pd.Series, jitter_seed: int = 0) -> np.ndarray:
    """Intervalos (s) entre chegadas. Os horários têm resolução de 1 s, então há empates;
    soma-se ruído uniforme em [0, 1) a cada horário, o que mantém a média sem intervalos nulos."""
    t = (pd.to_datetime(timestamps) - pd.Timestamp("1970-01-01")).dt.total_seconds().to_numpy(dtype=float)
    t = np.sort(np.floor(t) + np.random.default_rng(jitter_seed).random(len(t)))
    return np.diff(t)


def intervalos_por_faixa(
    timestamps: pd.Series, hours: tuple[int, int], weekdays_only: bool = True, jitter_seed: int = 0
) -> np.ndarray:
    """Intervalos dentro de cada dia, só na faixa de horas [h0, h1); nada atravessa a noite."""
    ts = pd.to_datetime(timestamps)
    keep = (ts.dt.hour >= hours[0]) & (ts.dt.hour < hours[1])
    if weekdays_only:
        keep &= ts.dt.day_of_week < 5
    ts = ts[keep]
    parts = [intervalos_chegada(day, jitter_seed + k) for k, (_, day) in enumerate(ts.groupby(ts.dt.date)) if len(day) > 1]
    return np.concatenate(parts) if parts else np.array([])


def _row(f) -> dict:
    return {
        "name": f.name,
        "rank": f.rank,
        "aic": float(f.aic),
        "bic": float(f.bic),
        "ks_stat": float(f.ks_stat),
        "sq_error": float(f.sq_error),
        "params": {k: float(v) for k, v in f.spec.params.items()},
    }


def analisar_valores(values, max_points: int = MAX_POINTS, seed: int = 0) -> dict:
    v = np.asarray(values, dtype=float)
    used = v if len(v) <= max_points else np.random.default_rng(seed).choice(v, max_points, replace=False)
    fits = fit_distributions(used)
    rows = [_row(f) for f in fits]
    best = fits[0].spec
    return {
        "n_total": int(len(v)),
        "n_usado": int(len(used)),
        "ranking": rows,
        "melhor": rows[0]["name"],
        "proposta": {"dist": best.dist, "params": {k: float(x) for k, x in best.params.items()}},
    }


def analisar_atendimento(calls: pd.DataFrame, max_points: int = MAX_POINTS) -> dict:
    served = calls[calls["outcome"] == "AGENT"]["ser_time_s"]
    values, report = clean_values(served.tolist())
    out = analisar_valores(values, max_points)
    out["limpeza"] = report
    return out


def exportar_nyc_horario(parquet: Path, out: Path) -> None:
    df = pd.read_parquet(parquet)[["hour_ts", "calls"]]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, compression="gzip")


def varrer_agentes(calls: pd.DataFrame, sampler, agents_list, wait_s: float, day_type: str, hours: tuple[int, int], seed: int = 0) -> list[dict]:
    """Repete a validação com vários números de agentes (calibração; o número obtido não equivale à equipe presente)."""
    rows = []
    for n in sorted({int(x) for x in agents_list}):
        r = replay_validation(calls, sampler, n, wait_s, day_type, hours, seed=seed)
        rows.append({"agentes": n, "sim_mean_wait_s": r["sim_mean_wait_s"], "sim_service_level": r["sim_service_level"]})
    return rows


def mais_proximo(rows: list[dict], real_wait_s: float) -> int:
    """Número de agentes cuja espera simulada fica mais perto da espera real (empate: o menor)."""
    return min(rows, key=lambda r: (abs(r["sim_mean_wait_s"] - real_wait_s), r["agentes"]))["agentes"]


def _busiest_weekday_hour(calls: pd.DataFrame) -> int:
    wd = calls[calls["date"].dt.day_of_week.isin([6, 0, 1, 2, 3]) & (calls["outcome"] == "AGENT")]
    return int((wd["entry_s"] // 3600).value_counts().idxmax())


def main() -> None:
    results = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}
    calls = pd.read_csv(EXEMPLOS / "technion_chamadas.csv.gz", parse_dates=["date"])

    atendimento = analisar_atendimento(calls)
    chegadas = results.get("analisador", {}).get("chegadas_nyc", [])
    if NYC_RAW.exists():
        created = pd.read_csv(NYC_RAW, usecols=["created_date"], parse_dates=["created_date"])["created_date"]
        chegadas = []
        for label, hrs in BANDS.items():
            r = analisar_valores(intervalos_por_faixa(created, hrs, weekdays_only=True))
            chegadas.append({"faixa": label, **{k: r[k] for k in ("n_total", "n_usado", "melhor")}, "ranking": r["ranking"][:3]})

    hour = _busiest_weekday_hour(calls)
    sampler = build_sampler(DistSpec(atendimento["proposta"]["dist"], atendimento["proposta"]["params"]))
    val = replay_validation(calls, sampler, BANK_AGENTS, WAIT_S, "weekday", (hour, hour + 1), seed=0)
    val.update({"agentes": BANK_AGENTS, "meta_espera_s": WAIT_S, "hora": hour,
                "dias": "dias úteis do banco (domingo a quinta)",
                "ressalva": "O banco real tem abandono de fila e o simulador não; só ligações atendidas entram como chegadas."})

    val["varredura"] = varrer_agentes(calls, sampler, range(4, 13), WAIT_S, "weekday", (hour, hour + 1))
    val["agentes_mais_proximo_espera"] = mais_proximo(val["varredura"], val["real_mean_wait_s"])

    results["analisador"] = {"atendimento_technion": atendimento, "chegadas_nyc": chegadas}
    results["validacao_banco"] = val
    RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    horario = ROOT / "data" / "processed" / "hourly.parquet"
    if horario.exists():
        exportar_nyc_horario(horario, EXEMPLOS / "nyc311_horario.csv.gz")
    print("OK", RESULTS)


if __name__ == "__main__":
    main()



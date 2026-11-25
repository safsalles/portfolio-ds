"""Lógica do app (sem Streamlit): padrões, upload do usuário e simulação."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from src.distributions import DistSpec, describe, spec_pdf
from src.erlang import agents_needed
from src.input_analyzer import clean_values, fit_distributions
from src.scenario import SimScenario, run_scenario

ROOT = Path(__file__).resolve().parents[1]
MAX_CALLS = 200_000
REPLICAS = 6  # o resultado principal e a varredura usam a mesma precisão, para os números baterem
MIN_POINTS = 30
UPLOAD_SAMPLE = 50_000  # máximo de pontos usados no ajuste de um arquivo do usuário
NY = "America/New_York"

SOURCE_NOTE = (
    "**Fontes misturadas:** as chegadas vêm do **NYC 311** (chamadas de telefone, 2024-2025) e o atendimento vem do call center "
    "**Technion Anonymous Bank** (Israel, 1999). As duas bases não têm relação entre si; o único elo real com o banco é a "
    "distribuição do tempo de atendimento. Equipe, metas e folga são fictícios."
)


def load_defaults(root: Path = ROOT) -> dict:
    """Tudo o que o app precisa para abrir sozinho: só results.json e data/exemplos."""
    root = Path(root)
    res = json.loads((root / "results" / "results.json").read_text(encoding="utf-8"))
    an = res["analisador"]["atendimento_technion"]
    proposal = DistSpec(an["proposta"]["dist"], an["proposta"]["params"])

    nyc = pd.read_csv(root / "data" / "exemplos" / "nyc311_horario.csv.gz", parse_dates=["hour_ts"])
    local = nyc["hour_ts"].dt.tz_localize("UTC").dt.tz_convert(NY)
    daytime = nyc[(local.dt.hour >= 9) & (local.dt.hour < 17) & (local.dt.day_of_week < 5)]
    calls_per_hour = float(round(daytime["calls"].median()))

    technion = pd.read_csv(root / "data" / "exemplos" / "technion_chamadas.csv.gz", usecols=["outcome", "ser_time_s"])
    values = technion[(technion["outcome"] == "AGENT") & (technion["ser_time_s"] > 0)]["ser_time_s"].to_numpy(dtype=float)
    if len(values) > UPLOAD_SAMPLE:
        values = np.random.default_rng(0).choice(values, UPLOAD_SAMPLE, replace=False)

    mean_service = describe(proposal, n=100_000)["mean"]
    return {
        "fits": an["ranking"],
        "proposal": proposal,
        "service_values": values,
        "calls_per_hour": calls_per_hour,
        "agents": agents_needed(calls_per_hour, mean_service, 0.8, 20),
        "mean_service": mean_service,
        "validation": res.get("validacao_banco", {}),
        "arrivals": res["analisador"].get("chegadas_nyc", []),
        "source_note": SOURCE_NOTE,
    }


def _read_column(text: str, column: str | None):
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("arquivo vazio")
    header = lines[0]
    has_header = any(ch.isalpha() for ch in header)
    delim = next((d for d in (";", "\t", ",") if d in header), None) if has_header else None
    names = [h.strip() for h in header.split(delim)] if (has_header and delim) else ([header.strip()] if has_header else ["valor"])
    body = lines[1:] if has_header else lines
    if column is None:
        idx = 0
    elif column in names:
        idx = names.index(column)
    else:
        raise ValueError(f"a coluna {column!r} não existe; colunas encontradas: {names}")
    rows = [(r.split(delim)[idx] if (delim and idx < len(r.split(delim))) else (r if not delim else "")) for r in body]
    return names, rows


def analyze_upload(file_bytes: bytes, column: str | None = None) -> dict:
    """Analisa o arquivo do usuário. Nunca levanta: devolve {"error": texto} se algo estiver errado."""
    try:
        if not file_bytes or not file_bytes.strip():
            return {"error": "arquivo vazio"}
        text = file_bytes.decode("utf-8-sig")
        _, rows = _read_column(text, column)
        values, report = clean_values(rows)
        if len(values) < MIN_POINTS:
            return {"error": f"poucos pontos válidos: {len(values)} (mínimo {MIN_POINTS}). Descartados: {report}"}
        used = values if len(values) <= UPLOAD_SAMPLE else np.random.default_rng(0).choice(values, UPLOAD_SAMPLE, replace=False)
        return {"values": values, "report": report, "fits": fit_distributions(used)}
    except UnicodeDecodeError:
        return {"error": "não consegui ler o arquivo como texto (use CSV em UTF-8)"}
    except Exception as exc:  # o app nunca deve quebrar por causa do arquivo do usuário
        return {"error": str(exc) or exc.__class__.__name__}


def simulate(
    service: DistSpec,
    arrival: DistSpec | None,
    calls_per_hour: float,
    agents: int,
    wait_s: int,
    sl_target: float,
    n_calls: int = 20000,
) -> dict:
    capped = n_calls > MAX_CALLS
    sc = SimScenario("app", service, arrival, float(calls_per_hour), int(agents), int(wait_s), float(sl_target))
    r = run_scenario(sc, n_calls=min(n_calls, MAX_CALLS), replicas=REPLICAS)
    r["capped"] = capped
    r["meets_target"] = r["sim_mean"] >= sl_target
    if not r["stable"]:
        r["warning"] = (
            f"Cenário instável: a carga ({r['traffic_erlangs']:.1f} erlangs) é maior ou igual ao número de agentes ({agents}); a fila cresce sem parar."
        )
    return r


def sweep_agents(
    service: DistSpec,
    arrival: DistSpec | None,
    calls_per_hour: float,
    wait_s: int,
    sl_target: float,
    agents_list,
    n_calls: int = 20000,
    replicas: int = REPLICAS,
) -> pd.DataFrame:
    """Nível de serviço e espera média para cada número de agentes (quanto muda ao contratar ou demitir)."""
    agents_list = [int(a) for a in agents_list]
    if not agents_list or min(agents_list) < 1:
        raise ValueError("informe ao menos um número de agentes >= 1")
    rows = []
    for a in agents_list:
        sc = SimScenario("sweep", service, arrival, float(calls_per_hour), a, int(wait_s), float(sl_target))
        r = run_scenario(sc, n_calls=min(n_calls, MAX_CALLS), replicas=replicas)
        rows.append({"agents": a, "service_level": r["sim_mean"], "wait_mean_s": r["wait_mean_s"], "stable": r["stable"]})
    return pd.DataFrame(rows)


def min_agents_for_target(sweep: pd.DataFrame, sl_target: float) -> int | None:
    """Menor número de agentes da varredura que atinge a meta (None se nenhum atinge)."""
    ok = sweep[sweep["service_level"] >= sl_target]
    return int(ok["agents"].min()) if len(ok) else None


def plot_fits(values: np.ndarray, specs: list[tuple[str, DistSpec]], bins: int = 40) -> Figure:
    v = np.asarray(values, dtype=float)
    top = float(np.percentile(v, 99.5))
    fig = Figure(figsize=(9, 3.6))
    ax = fig.subplots()
    ax.hist(v[v <= top], bins=bins, density=True, color="#cccccc", label="dados / data")
    xs = np.linspace(max(float(v.min()), 1e-9), top, 400)
    for label, spec in specs:
        ax.plot(xs, spec_pdf(spec)(xs), label=label)
    ax.set_xlabel("segundos / seconds")
    ax.set_ylabel("densidade / density")
    ax.legend()
    fig.tight_layout()
    return fig




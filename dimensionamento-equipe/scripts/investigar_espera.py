"""Roda a investigação sobre a espera do banco e grava results.json["investigacao"].

Precisa dos arquivos originais em data/raw/technion. Dias úteis do banco (domingo a quinta).
Os cortes e critérios abaixo foram fixados antes de ver os resultados de cada passo.

Uso: python scripts/investigar_espera.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import investigacao as inv  # noqa: E402
from src.distributions import DistSpec, build_sampler  # noqa: E402
from src.simulation import queue_waits  # noqa: E402

RAW = ROOT / "data" / "raw" / "technion"
RESULTS = ROOT / "results" / "results.json"
WEEKDAYS = [6, 0, 1, 2, 3]
BREAK_MINUTES = [2, 5, 10]  # principal: 5; 2 e 10 mostram a sensibilidade
FREE_DELAY_S = 10  # atraso "relevante": mediana >= 10 s com gente livre
WAIT_S = 20
HOUR = 10

LABELS = {
    "real": ("Real", "Real"),
    "fixo8": ("8 fixos", "8 fixed"),
    "presenca": ("Atendentes medidos (presença na hora)", "Measured agents (present in the hour)"),
    "turno": ("Atendentes medidos (turno)", "Measured agents (shift)"),
    "fixo8_A": ("8 fixos + intervalo A", "8 fixed + gap A"),
    "fixo8_B": ("8 fixos + intervalo B", "8 fixed + gap B"),
    "presenca_A": ("Medidos + intervalo A", "Measured + gap A"),
    "presenca_B": ("Medidos + intervalo B", "Measured + gap B"),
    **{k: v for m in BREAK_MINUTES for k, v in (
        (f"pausas{m}", (f"Medidos com pausas de {m} min ou mais", f"Measured with breaks of {m} min or more")),
        (f"pausas{m}_A", (f"Medidos com pausas de {m} min ou mais + intervalo A", f"Measured with breaks of {m} min or more + gap A")),
    )},
}


def _stats(x: pd.Series) -> dict:
    return {"espera_media_s": float(x.mean()), "nivel_servico": float(np.mean(x <= WAIT_S)), "mediana_s": float(x.median())}


def _free_stats(frame: pd.DataFrame) -> dict:
    free = frame[frame["free"]]
    return {
        "ligacoes": int(len(free)),
        "fracao_do_total": float(len(free) / len(frame)),
        "fracao_na_fila": float(free["queued"].mean()),
        "mediana_s": float(free["q"].median()),
        "media_s": float(free["q"].mean()),
    }


def main() -> None:
    lines: list[str] = []
    for f in sorted(RAW.glob("*.txt")):
        lines.extend(f.read_text(encoding="utf-8", errors="replace").splitlines())
    calls = inv.parse_bruto(lines)
    calls = calls[calls["date"].dt.day_of_week.isin(WEEKDAYS)]
    served = calls[calls["outcome"] == "AGENT"]

    pres, shift = inv.presence(calls), inv.shift_presence(calls)
    gap_a = inv.switch_gaps(calls)
    gap_b = inv.queue_gaps(calls, inv.queue_union(calls, tol=2), tol=2)
    union = inv.queue_union(calls, tol=0)
    brk = {m: inv.breaks(calls, union, m * 60) for m in BREAK_MINUTES}

    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    p = res["analisador"]["atendimento_technion"]["proposta"]
    sampler = build_sampler(DistSpec(p["dist"], p["params"]))

    parts = []
    available: dict = {m: [] for m in [0] + BREAK_MINUTES}  # atendentes disponíveis 10h-11h (média no tempo)
    for k, (date, day) in enumerate(served.groupby("date")):
        day = day.sort_values("entry_s", kind="stable")
        arr = day["entry_s"].to_numpy(float)
        rng = np.random.default_rng(k)
        svc = sampler(rng, len(arr))
        if not any(pres.get((date, h)) for h in range(24)):
            continue
        wa = rng.choice(gap_a, len(arr))
        wb = rng.choice(gap_b, len(arr))
        points, caps = inv.capacity(date, pres)
        spoints, scaps = inv.capacity(date, shift)
        row = {
            "hour": (arr // 3600).astype(int),
            "real": day["q_time"].to_numpy(float),
            "fixo8": queue_waits(arr, svc, 8),
            "fixo8_A": queue_waits(arr, svc + wa, 8),
            "fixo8_B": queue_waits(arr, svc + wb, 8),
            "presenca": inv.varying_waits(arr, svc, points, caps),
            "presenca_A": inv.varying_waits(arr, svc + wa, points, caps),
            "presenca_B": inv.varying_waits(arr, svc + wb, points, caps),
            "turno": inv.varying_waits(arr, svc, spoints, scaps),
        }
        for m in [0] + BREAK_MINUTES:
            pts, cps = (points, caps) if m == 0 else inv.capacity(date, pres, brk[m])
            lo, hi = HOUR * 3600, (HOUR + 1) * 3600
            available[m].append(sum(c * max(0, min(pts[i + 1], hi) - max(pts[i], lo)) for i, c in enumerate(cps[:-1])) / 3600)
            if m:
                row[f"pausas{m}"] = inv.varying_waits(arr, svc, pts, cps)
                row[f"pausas{m}_A"] = inv.varying_waits(arr, svc + wa, pts, cps)
        parts.append(pd.DataFrame(row))
    o = pd.concat(parts, ignore_index=True)
    window, whole = o[o["hour"] == HOUR], o[o["hour"] >= 7]

    free = inv.free_situation(calls[calls["outcome"].isin(["AGENT", "HANG"])], pres)
    free_day = free[free["hour"] >= 7]

    res["investigacao"] = {
        "hora": HOUR,
        "meta_espera_s": WAIT_S,
        "ligacoes_janela": int(len(window)),
        "cenarios": [
            {"chave": key, "rotulo_pt": pt, "rotulo_en": en, "janela": _stats(window[key]), "dia": _stats(whole[key])}
            for key, (pt, en) in LABELS.items()
        ],
        "intervalos": {
            name: {"n": int(len(g)), "media_s": float(g.mean()), "mediana_s": float(np.median(g))}
            for name, g in (("A", gap_a), ("B", gap_b))
        },
        "disponiveis_na_janela": {str(m): float(np.mean(v)) for m, v in available.items()},
        "livre": {
            "janela": _free_stats(free[free["hour"] == HOUR]),
            "dia": _free_stats(free_day),
            "criterio_mediana_s": FREE_DELAY_S,
            "relevante": bool(free_day[free_day["free"]]["q"].median() >= FREE_DELAY_S),
        },
    }
    RESULTS.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("OK", RESULTS)


if __name__ == "__main__":
    main()

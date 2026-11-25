"""Investigação: por que a simulação não reproduz a espera do banco (Technion)?

Trabalha sobre os arquivos originais, que trazem quem atendeu cada ligação. Só agregados
saem daqui: nomes de atendentes não são gravados. Os horários são segundos do dia e o
DataFrame esperado é o de `parse_bruto` (uma linha por ligação).
"""
from __future__ import annotations

import heapq
from bisect import bisect_right
from typing import Iterable

import numpy as np
import pandas as pd

HOUR = 3600


def _hms(text: str) -> int:
    h, m, s = text.split(":")
    return int(h) * HOUR + int(m) * 60 + int(s)


def parse_bruto(lines: Iterable[str]) -> pd.DataFrame:
    rows = []
    for line in lines:
        f = line.split()
        if len(f) != 17 or f[0].startswith("vru"):
            continue
        rows.append((f[5], _hms(f[6]), _hms(f[7]), _hms(f[9]), _hms(f[10]), int(f[11]), f[12], _hms(f[13]), _hms(f[14]), f[16]))
    df = pd.DataFrame(
        rows,
        columns=["date", "entry_s", "vru_exit", "q_start", "q_exit", "q_time", "outcome", "ser_start", "ser_exit", "server"],
    )
    df["date"] = pd.to_datetime("19" + df["date"], format="%Y%m%d")
    return df


def _named(df: pd.DataFrame) -> pd.DataFrame:
    """Ligações atendidas com atendente identificado e horários coerentes."""
    return df[(df["outcome"] == "AGENT") & (df["server"] != "NO_SERVER") & (df["ser_exit"] >= df["ser_start"])]


def _by_agent(df: pd.DataFrame):
    for key, g in _named(df).groupby(["date", "server"]):
        yield key, g.sort_values("ser_start")


def presence(df: pd.DataFrame) -> dict:
    """(data, hora) -> atendentes com alguma ligação que ocupou aquela hora."""
    out: dict = {}
    for (date, name), g in _by_agent(df):
        for a, b in zip(g["ser_start"], g["ser_exit"]):
            for h in range(a // HOUR, min(b // HOUR, 23) + 1):
                out.setdefault((date, h), set()).add(name)
    return out


def shift_presence(df: pd.DataFrame) -> dict:
    """Medida alternativa: presente da primeira à última ligação do dia."""
    out: dict = {}
    for (date, name), g in _by_agent(df):
        for h in range(g["ser_start"].min() // HOUR, min(g["ser_exit"].max() // HOUR, 23) + 1):
            out.setdefault((date, h), set()).add(name)
    return out


def queue_union(df: pd.DataFrame, tol: int = 0) -> dict:
    """data -> (inícios, fins) dos períodos com alguém na fila."""
    out = {}
    q = df[(df["q_start"] > 0) & (df["q_exit"] > df["q_start"])]
    for date, g in q.groupby("date"):
        starts: list = []
        ends: list = []
        for a, b in sorted(zip(g["q_start"], g["q_exit"])):
            if ends and a <= ends[-1] + tol:
                ends[-1] = max(ends[-1], b)
            else:
                starts.append(a)
                ends.append(b)
        out[date] = (starts, ends)
    return out


def switch_gaps(df: pd.DataFrame) -> np.ndarray:
    """A: o próximo cliente do atendente já estava na fila quando ele desligou."""
    gaps: list = []
    for _, g in _by_agent(df):
        t = g["ser_exit"].to_numpy()[:-1]
        nxt = g.iloc[1:]
        qs, s = nxt["q_start"].to_numpy(), nxt["ser_start"].to_numpy()
        ok = (qs > 0) & (qs <= t) & (s >= t)
        gaps.extend((s - t)[ok])
    return np.array(gaps, dtype=float)


def queue_gaps(df: pd.DataFrame, union: dict, tol: int = 2) -> np.ndarray:
    """B: houve alguém esperando durante todo o intervalo até a próxima ligação."""
    gaps: list = []
    for (date, _), g in _by_agent(df):
        if date not in union:
            continue
        starts, ends = union[date]
        for t, s in zip(g["ser_exit"].to_numpy()[:-1], g["ser_start"].to_numpy()[1:]):
            i = bisect_right(starts, t + tol) - 1
            if s >= t and i >= 0 and ends[i] >= s - tol and ends[i] > t:
                gaps.append(s - t)
    return np.array(gaps, dtype=float)


def breaks(df: pd.DataFrame, union: dict, min_s: int) -> dict:
    """data -> [(atendente, início, fim)]: intervalo >= min_s com alguém na fila em algum momento."""
    out: dict = {}
    for (date, name), g in _by_agent(df):
        if date not in union:
            continue
        starts, ends = union[date]
        for t, s in zip(g["ser_exit"].to_numpy()[:-1], g["ser_start"].to_numpy()[1:]):
            if s - t < min_s:
                continue
            i = bisect_right(starts, s - 1) - 1
            if i >= 0 and ends[i] > t:
                out.setdefault(date, []).append((name, int(t), int(s)))
    return out


def capacity(date, pres: dict, breaks_by_date: dict | None = None) -> tuple[list, list]:
    """Pontos de mudança e capacidade: presentes na hora menos os (dentre eles) em pausa."""
    br = (breaks_by_date or {}).get(date, [])
    points = sorted({h * HOUR for h in range(25)} | {t for _, a, b in br for t in (a, b)})
    caps = []
    for p in points:
        away = {n for n, a, b in br if a <= p < b}
        caps.append(len(pres.get((date, p // HOUR), set()) - away))
    return points, caps


def varying_waits(arrivals: np.ndarray, services: np.ndarray, points: list, caps: list) -> np.ndarray:
    """Fila FIFO com capacidade que muda no tempo; quem está atendendo termina a ligação.
    Depois do último período com alguém, mantém a última capacidade positiva."""
    last_pos = max(i for i, c in enumerate(caps) if c > 0)
    busy: list = []
    waits, last = np.empty(len(arrivals)), 0.0
    for i, a in enumerate(arrivals):
        s = max(a, last)
        while True:
            while busy and busy[0] <= s:
                heapq.heappop(busy)
            k = bisect_right(points, s) - 1
            c = caps[k] if k <= last_pos else caps[last_pos]
            if len(busy) < c:
                break
            options = [v for v in (busy[0] if busy else None, points[k + 1] if k + 1 <= last_pos else None) if v is not None]
            s = min(options) if options else points[k + 1]
        waits[i], last = s - a, s
        heapq.heappush(busy, s + services[i])
    return waits


def free_situation(df: pd.DataFrame, pres: dict) -> pd.DataFrame:
    """Para cada ligação atendida: quantos estavam à frente e ocupados quando ela entrou.
    "Livre" = ninguém na fila e no máximo metade dos presentes ocupada."""
    rows = []
    for date, day in df.groupby("date"):
        served = _named(day)
        s0, s1 = np.sort(served["ser_start"].to_numpy()), np.sort(served["ser_exit"].to_numpy())
        q = day[(day["q_start"] > 0) & (day["q_exit"] >= day["q_start"])]
        qs, qe = np.sort(q["q_start"].to_numpy()), np.sort(q["q_exit"].to_numpy())
        for r in day[day["outcome"] == "AGENT"].itertuples():
            t = r.q_start if r.q_start > 0 else r.vru_exit
            busy = int(np.searchsorted(s0, t, "right") - np.searchsorted(s1, t, "right"))
            ahead = max(0, int(np.searchsorted(qs, t, "left") - np.searchsorted(qe, t, "right")))
            present = len(pres.get((date, t // HOUR), ()))
            if present:
                rows.append((date, t, t // HOUR, r.q_time, r.q_start > 0, busy, ahead, present))
    out = pd.DataFrame(rows, columns=["date", "t", "hour", "q", "queued", "busy", "ahead", "present"])
    out["free"] = (out["ahead"] == 0) & (out["busy"] <= out["present"] / 2)
    return out

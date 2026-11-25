import numpy as np
import pandas as pd
import pytest

from src.investigacao import (
    breaks,
    capacity,
    free_situation,
    parse_bruto,
    presence,
    queue_gaps,
    queue_union,
    switch_gaps,
    varying_waits,
)
from src.simulation import queue_waits

D = pd.Timestamp("1999-01-03")


def calls(rows):
    """rows: (qs, qe, outcome, s0, s1, server)"""
    out = pd.DataFrame(rows, columns=["q_start", "q_exit", "outcome", "ser_start", "ser_exit", "server"])
    out["date"] = D
    out["q_time"] = out["q_exit"] - out["q_start"]
    out["entry_s"] = np.where(out["q_start"] > 0, out["q_start"], out["ser_start"])
    out["vru_exit"] = out["entry_s"]
    return out


def test_parse_bruto_reads_server_and_times():
    line = "AA0101\t90001\t1000002\t2\tPS\t990101\t6:55:20\t6:55:26\t6\t6:55:26\t6:55:43\t17\tAGENT\t6:55:43\t6:56:37\t54\tAGENTE_A"
    df = parse_bruto(["vru+line\tx", line, "lixo"])
    r = df.iloc[0]
    assert len(df) == 1 and r["server"] == "AGENTE_A"
    assert (r["q_start"], r["q_time"], r["ser_start"], r["ser_exit"]) == (24926, 17, 24943, 24997)


def test_varying_waits_matches_constant_capacity():
    rng = np.random.default_rng(1)
    arr = np.sort(rng.uniform(0, 36000, 500))
    svc = rng.exponential(200, 500)
    pts = [h * 3600 for h in range(25)]
    assert np.allclose(varying_waits(arr, svc, pts, [4] * 25), queue_waits(arr, svc, 4))


def test_varying_waits_agent_leaving_makes_caller_wait():
    # 1 agente até 100 s, nenhum até 200 s, 1 depois: quem chega em 150 espera 50 s
    w = varying_waits(np.array([150.0]), np.array([10.0]), [0, 100, 200], [1, 0, 1])
    assert w[0] == pytest.approx(50.0)


def test_switch_and_queue_gaps_definitions():
    c = calls([
        (0, 0, "AGENT", 100, 200, "A"),
        (150, 230, "AGENT", 230, 300, "A"),   # já esperava quando A desligou (200): troca = 30 s
        (400, 420, "AGENT", 420, 500, "A"),   # fila começou depois: não é troca nem fila contínua
    ])
    assert list(switch_gaps(c)) == [30]
    assert list(queue_gaps(c, queue_union(c, tol=2), tol=2)) == [30]


def test_breaks_need_length_and_someone_waiting():
    c = calls([
        (0, 0, "AGENT", 100, 200, "A"),
        (0, 0, "AGENT", 900, 950, "A"),     # 700 s sem atender, com alguém na fila (abaixo): pausa
        (0, 0, "AGENT", 2000, 2050, "A"),   # 1050 s sem atender, ninguém esperou: não é pausa
        (300, 350, "HANG", 0, 0, "NO_SERVER"),
    ])
    q = queue_union(c, tol=0)
    assert breaks(c, q, 300)[D] == [("A", 200, 900)]
    assert breaks(c, q, 800).get(D, []) == []


def test_capacity_subtracts_only_present_agents_on_break():
    pres = {(D, 0): {"A", "B"}}
    br = {D: [("A", 100, 200), ("Z", 100, 200)]}
    pts, caps = capacity(D, pres, br)
    at = lambda t: caps[max(i for i, p in enumerate(pts) if p <= t)]
    assert at(50) == 2 and at(150) == 1 and at(250) == 2


def test_presence_counts_agents_with_a_call_in_the_hour():
    c = calls([(0, 0, "AGENT", 3500, 3700, "A"), (0, 0, "AGENT", 100, 200, "B")])
    p = presence(c)
    assert p[(D, 0)] == {"A", "B"} and p[(D, 1)] == {"A"}


def test_free_situation_flags_empty_queue_and_half_busy():
    c = calls([
        (0, 0, "AGENT", 100, 1000, "A"),
        (0, 0, "AGENT", 100, 110, "B"),
        (0, 0, "AGENT", 100, 110, "C"),
        (0, 0, "AGENT", 100, 110, "E"),
        (500, 540, "AGENT", 540, 560, "B"),   # 1 ocupado de 4, sem fila: livre
        (520, 570, "AGENT", 570, 580, "C"),   # alguém na frente: não é livre
    ])
    r = free_situation(c, presence(c))
    flags = dict(zip(r["t"], r["free"]))
    assert flags[500] is True or flags[500] == True  # noqa: E712
    assert not flags[520]

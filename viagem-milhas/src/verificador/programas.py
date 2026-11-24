"""Painel por programa de milhas: quanto custa a passagem em milhas (com bonus de transferencia) x dinheiro."""
import csv
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProgramInput:
    program: str
    milheiro_brl: float   # preco de compra de 1.000 pontos/milhas
    bonus_pct: float      # bonus de transferencia (ex.: 100 = dobra)
    miles: int            # milhas que a passagem pede (viagem toda)
    taxes_brl: float
    balance: int = 0      # milhas/pontos que voce ja tem no programa
    price_date: str = ""  # quando o preco do milheiro foi visto (AAAA-MM-DD)


@dataclass(frozen=True)
class ProgramResult:
    program: str
    effective_milheiro: float | None
    miles_cost_brl: float | None
    saving_brl: float | None   # positivo = milhas ganham
    miles_win: bool


def evaluate(p: ProgramInput, cash_brl: float) -> ProgramResult:
    if p.milheiro_brl <= 0 or p.miles <= 0:
        return ProgramResult(p.program, None, None, None, False)
    eff = p.milheiro_brl / (1 + p.bonus_pct / 100)
    to_buy = max(0, p.miles - p.balance)  # o saldo que voce ja tem nao custa nada
    cost = to_buy / 1000 * eff + p.taxes_brl
    saving = cash_brl - cost if cash_brl > 0 else None
    return ProgramResult(p.program, eff, cost, saving, saving is not None and saving > 0)


def load_inputs(path: str, programs: list[str]) -> list[ProgramInput]:
    saved: dict[str, ProgramInput] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                saved[r["program"]] = ProgramInput(r["program"], float(r["milheiro_brl"]), float(r["bonus_pct"]),
                                                   int(float(r["miles"])), float(r["taxes_brl"]),
                                                   int(float(r.get("balance") or 0)), r.get("price_date") or "")
    return [saved.get(name, ProgramInput(name, 0.0, 0.0, 0, 0.0)) for name in programs]


def save_inputs(path: str, items: list[ProgramInput]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["program", "milheiro_brl", "bonus_pct", "miles", "taxes_brl", "balance", "price_date"])
        for i in items:
            w.writerow([i.program, i.milheiro_brl, i.bonus_pct, i.miles, i.taxes_brl, i.balance, i.price_date])


def max_miles_worth(cash_brl: float, taxes_brl: float, effective_milheiro: float) -> int | None:
    """Ate quantas milhas a passagem pode pedir e ainda custar menos que o dinheiro."""
    if cash_brl <= taxes_brl or effective_milheiro <= 0:
        return None
    return int((cash_brl - taxes_brl) / effective_milheiro * 1000)


def pick_milheiro(program: str, found: dict[str, float], limits: dict[str, float]) -> tuple[float, str]:
    if program in found:
        return found[program], "promoção achada"
    return limits[program], "seu limite"

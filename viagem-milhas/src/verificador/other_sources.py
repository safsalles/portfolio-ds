"""Leituras feitas fora do coletor automatico (Kayak, CVC, Flying Blue, TAP...).

Quem faz a leitura (o Claude, a pedido do Sergio) grava aqui com:
  python -m verificador.other_sources --source kayak --price 19152 --note "KLM Light"
"""
import argparse
import csv
import os
from dataclasses import dataclass
from datetime import date as _date

DEFAULT_PATH = "data/outras_fontes.csv"
FIELDS = ["date", "source", "price_brl", "miles", "taxes_brl", "note"]


@dataclass(frozen=True)
class OtherCheck:
    date: str
    source: str
    price_brl: float | None
    miles: int | None
    taxes_brl: float | None
    note: str


def append_check(path: str, check: OtherCheck) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    new_file = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        if new_file:
            writer.writeheader()
        writer.writerow(
            {
                "date": check.date,
                "source": check.source,
                "price_brl": "" if check.price_brl is None else str(float(check.price_brl)),
                "miles": "" if check.miles is None else str(int(check.miles)),
                "taxes_brl": "" if check.taxes_brl is None else str(float(check.taxes_brl)),
                "note": check.note,
            }
        )


def load_checks(path: str) -> list[OtherCheck]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [
            OtherCheck(
                r["date"],
                r["source"],
                float(r["price_brl"]) if r["price_brl"] else None,
                int(r["miles"]) if r["miles"] else None,
                float(r["taxes_brl"]) if r["taxes_brl"] else None,
                r["note"],
            )
            for r in csv.DictReader(f)
        ]


def latest_by_source(checks: list[OtherCheck]) -> dict[str, OtherCheck]:
    latest: dict[str, OtherCheck] = {}
    for c in checks:  # em empate de data, vale a ultima gravada
        if c.source not in latest or c.date >= latest[c.source].date:
            latest[c.source] = c
    return latest


def main() -> None:
    p = argparse.ArgumentParser(description="Grava uma leitura de outra fonte")
    p.add_argument("--source", required=True)
    p.add_argument("--price", type=float)
    p.add_argument("--miles", type=int)
    p.add_argument("--taxes", type=float)
    p.add_argument("--note", default="")
    p.add_argument("--date", default=_date.today().isoformat())
    p.add_argument("--path", default=DEFAULT_PATH)
    a = p.parse_args()
    append_check(a.path, OtherCheck(a.date, a.source.lower(), a.price, a.miles, a.taxes, a.note))
    print(f"gravado em {a.path}: {a.source} ({a.date})")


if __name__ == "__main__":
    main()

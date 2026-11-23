"""Consultas salvas: cada consulta guarda TODAS as ofertas achadas, para rever e comparar depois."""
import json
import os
from dataclasses import dataclass
from datetime import datetime

from verificador.config import Config
from verificador.models import Leg, Offer
from verificador.rules import is_compliant

DEFAULT_DIR = "data/snapshots"


@dataclass(frozen=True)
class SnapshotMeta:
    path: str
    saved_at: datetime
    source: str  # "agendada" (rotina diaria) ou "manual" (botao do app)
    best_total_brl: float | None
    n_offers: int


def _leg_dict(leg: Leg) -> dict:
    return {
        "origin": leg.origin,
        "destination": leg.destination,
        "airlines": list(leg.airlines),
        "layovers": [{"airport": l.airport, "minutes": l.minutes} for l in leg.layovers],
    }


def save_snapshot(directory: str, cfg: Config, offers: list[Offer], source: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    rules = cfg.rules
    rows = [
        {
            "total_price_brl": float(o.total_price_brl),
            "outbound": _leg_dict(o.outbound),
            "inbound": _leg_dict(o.inbound),
            "compliant": is_compliant(o, rules.min_layover_minutes, rules.avoid_airports, rules.max_layover_minutes),
        }
        for o in sorted(offers, key=lambda o: o.total_price_brl)
    ]
    passing = [r["total_price_brl"] for r in rows if r["compliant"]]
    data = {
        "saved_at": now.isoformat(timespec="seconds"),
        "source": source,
        "trip": {
            "outbound": list(cfg.trip.outbound),
            "inbound": list(cfg.trip.inbound),
            "adults": cfg.trip.adults,
            "cabin": cfg.trip.cabin,
            "currency": cfg.trip.currency,
        },
        "min_layover_minutes": rules.min_layover_minutes,
        "max_layover_minutes": rules.max_layover_minutes,
        "offers": rows,
        "best_total_brl": min(passing) if passing else None,
    }
    os.makedirs(directory, exist_ok=True)
    base = os.path.join(directory, f"{now:%Y-%m-%d_%H-%M-%S}")
    path, n = base + ".json", 1
    while os.path.exists(path):  # duas consultas no mesmo segundo nao se sobrescrevem
        path, n = f"{base}-{n}.json", n + 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_snapshot(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_snapshots(directory: str) -> list[SnapshotMeta]:
    if not os.path.isdir(directory):
        return []
    metas = []
    for name in os.listdir(directory):
        if not name.endswith(".json"):
            continue
        path = os.path.join(directory, name)
        try:
            data = load_snapshot(path)
            metas.append(
                SnapshotMeta(
                    path,
                    datetime.fromisoformat(data["saved_at"]),
                    data["source"],
                    data["best_total_brl"],
                    len(data["offers"]),
                )
            )
        except (OSError, ValueError, KeyError):
            continue  # arquivo estranho na pasta nao derruba a listagem
    return sorted(metas, key=lambda m: m.saved_at, reverse=True)


def describe_layovers(layovers: list[dict]) -> str:
    if not layovers:
        return "direto"
    parts = []
    for l in layovers:
        m = l["minutes"]
        parts.append(f"{l['airport']} ?" if m is None else f"{l['airport']} {m // 60}h{m % 60:02d}")
    return " + ".join(parts)


def offer_rows(snapshot: dict) -> list[dict]:
    rows = []
    for o in snapshot["offers"]:
        airlines = dict.fromkeys(o["outbound"]["airlines"] + o["inbound"]["airlines"])
        rows.append(
            {
                "Total (R$)": o["total_price_brl"],
                "Companhias": "+".join(airlines),
                "Escalas da ida": describe_layovers(o["outbound"]["layovers"]),
                "Escalas da volta": describe_layovers(o["inbound"]["layovers"]),
                "Passa nas regras": "Sim" if o["compliant"] else "Não",
            }
        )
    return sorted(rows, key=lambda r: r["Total (R$)"])


def compare_best(new: float | None, old: float | None) -> tuple[float, float] | None:
    """Diferenca (R$ e %) entre o melhor preco de duas consultas; None se faltar um deles."""
    if new is None or old is None or old == 0:
        return None
    delta = new - old
    return delta, delta / old * 100

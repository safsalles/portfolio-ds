import tomllib
from dataclasses import dataclass


@dataclass(frozen=True)
class Trip:
    outbound: tuple[str, str, str]  # origem, destino, data (AAAA-MM-DD)
    inbound: tuple[str, str, str]
    adults: int
    cabin: str
    currency: str


@dataclass(frozen=True)
class Rules:
    min_layover_minutes: int
    avoid_airports: frozenset[str]  # aeroportos onde voce NAO aceita fazer escala (opcional)
    max_layover_minutes: int | None = None  # escala maxima aceita; None = sem limite


@dataclass(frozen=True)
class Alerts:
    drop_pct: float
    target_brl: float


@dataclass(frozen=True)
class Promos:
    feeds: tuple[str, ...]
    keywords: tuple[str, ...]
    max_milheiro: dict[str, float]


@dataclass(frozen=True)
class Paths:
    history: str
    seen_promos: str
    alerts_log: str
    snapshots: str = "data/snapshots"  # consultas salvas (todas as ofertas de cada consulta)


@dataclass(frozen=True)
class Baggage:
    carry_on: int  # malas de mao POR PESSOA
    checked: int  # malas despachadas no total, por trecho
    checked_bag_fee_brl: float  # preco estimado de UMA mala despachada, por trecho
    send_to_api: bool = False  # enviar a mala de mao ao Google Voos (filtra ofertas; desligado por padrao)


@dataclass(frozen=True)
class Config:
    trip: Trip
    rules: Rules
    alerts: Alerts
    promos: Promos
    paths: Paths
    baggage: Baggage = Baggage(0, 0, 0.0)


def load_config(path: str = "config.toml") -> Config:
    with open(path, "rb") as f:
        raw = tomllib.loads(f.read().decode("utf-8-sig"))  # aceita UTF-8 com BOM (Bloco de Notas, PowerShell 5)
    t, r, a, p, d = raw["trip"], raw["rules"], raw["alerts"], raw["promos"], raw["paths"]
    b = raw.get("baggage", {})
    return Config(
        trip=Trip(
            outbound=tuple(t["outbound"]),
            inbound=tuple(t["inbound"]),
            adults=t["adults"],
            cabin=t["cabin"],
            currency=t["currency"],
        ),
        rules=Rules(
            min_layover_minutes=r["min_layover_minutes"],
            avoid_airports=frozenset(r.get("avoid_airports", [])),
            max_layover_minutes=int(r.get("max_layover_minutes", 0)) or None,  # 0 ou ausente = sem limite
        ),
        alerts=Alerts(drop_pct=float(a["drop_pct"]), target_brl=float(a["target_brl"])),
        promos=Promos(
            feeds=tuple(p["feeds"]),
            keywords=tuple(p["keywords"]),
            max_milheiro={k: float(v) for k, v in p["max_milheiro"].items()},
        ),
        paths=Paths(
            history=d["history"],
            seen_promos=d["seen_promos"],
            alerts_log=d["alerts_log"],
            snapshots=d.get("snapshots", "data/snapshots"),
        ),
        baggage=Baggage(
            carry_on=int(b.get("carry_on", 0)),
            checked=int(b.get("checked", 0)),
            checked_bag_fee_brl=float(b.get("checked_bag_fee_brl", 0.0)),
            send_to_api=bool(b.get("send_to_api", False)),
        ),
    )

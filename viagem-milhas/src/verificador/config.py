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
    brazil_airports: frozenset[str]


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


@dataclass(frozen=True)
class Config:
    trip: Trip
    rules: Rules
    alerts: Alerts
    promos: Promos
    paths: Paths


def load_config(path: str = "config.toml") -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    t, r, a, p, d = raw["trip"], raw["rules"], raw["alerts"], raw["promos"], raw["paths"]
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
            brazil_airports=frozenset(r["brazil_airports"]),
        ),
        alerts=Alerts(drop_pct=float(a["drop_pct"]), target_brl=float(a["target_brl"])),
        promos=Promos(
            feeds=tuple(p["feeds"]),
            keywords=tuple(p["keywords"]),
            max_milheiro={k: float(v) for k, v in p["max_milheiro"].items()},
        ),
        paths=Paths(history=d["history"], seen_promos=d["seen_promos"], alerts_log=d["alerts_log"]),
    )

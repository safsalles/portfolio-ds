from dataclasses import dataclass


@dataclass(frozen=True)
class Layover:
    airport: str
    minutes: int | None  # None = a API nao informou a duracao


@dataclass(frozen=True)
class Leg:
    origin: str
    destination: str
    airlines: tuple[str, ...]
    layovers: tuple[Layover, ...]


@dataclass(frozen=True)
class Offer:
    total_price_brl: float
    outbound: Leg
    inbound: Leg
    fare: str | None

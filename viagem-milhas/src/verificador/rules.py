from verificador.models import Layover, Leg, Offer


def _layover_ok(layover: Layover, min_minutes: int, brazil_airports: frozenset[str]) -> bool:
    if layover.airport in brazil_airports:
        return False
    if layover.minutes is None:
        return False
    return layover.minutes >= min_minutes


def leg_is_compliant(leg: Leg, min_layover_minutes: int, brazil_airports: frozenset[str]) -> bool:
    return all(_layover_ok(l, min_layover_minutes, brazil_airports) for l in leg.layovers)


def is_compliant(offer: Offer, min_layover_minutes: int, brazil_airports: frozenset[str]) -> bool:
    return leg_is_compliant(offer.outbound, min_layover_minutes, brazil_airports) and leg_is_compliant(
        offer.inbound, min_layover_minutes, brazil_airports
    )


def _has_unknown_duration(offer: Offer) -> bool:
    return any(l.minutes is None for l in offer.outbound.layovers + offer.inbound.layovers)


def cheapest_compliant(
    offers: list[Offer], min_layover_minutes: int, brazil_airports: frozenset[str]
) -> tuple[Offer | None, int]:
    passing = [o for o in offers if is_compliant(o, min_layover_minutes, brazil_airports)]
    discarded_unknown = sum(
        1
        for o in offers
        if _has_unknown_duration(o) and not is_compliant(o, min_layover_minutes, brazil_airports)
    )
    best = min(passing, key=lambda o: o.total_price_brl, default=None)
    return best, discarded_unknown

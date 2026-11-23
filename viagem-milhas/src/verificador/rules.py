from verificador.models import Layover, Leg, Offer


def _layover_ok(
    layover: Layover, min_minutes: int, avoid_airports: frozenset[str], max_minutes: int | None = None
) -> bool:
    if layover.airport in avoid_airports:
        return False
    if layover.minutes is None:
        return False
    if layover.minutes < min_minutes:
        return False
    return max_minutes is None or layover.minutes <= max_minutes


def leg_is_compliant(
    leg: Leg, min_layover_minutes: int, avoid_airports: frozenset[str], max_layover_minutes: int | None = None
) -> bool:
    return all(_layover_ok(l, min_layover_minutes, avoid_airports, max_layover_minutes) for l in leg.layovers)


def is_compliant(
    offer: Offer, min_layover_minutes: int, avoid_airports: frozenset[str], max_layover_minutes: int | None = None
) -> bool:
    return leg_is_compliant(offer.outbound, min_layover_minutes, avoid_airports, max_layover_minutes) and leg_is_compliant(
        offer.inbound, min_layover_minutes, avoid_airports, max_layover_minutes
    )


def _has_unknown_duration(offer: Offer) -> bool:
    return any(l.minutes is None for l in offer.outbound.layovers + offer.inbound.layovers)


def cheapest_compliant(
    offers: list[Offer],
    min_layover_minutes: int,
    avoid_airports: frozenset[str],
    max_layover_minutes: int | None = None,
) -> tuple[Offer | None, int]:
    def ok(o: Offer) -> bool:
        return is_compliant(o, min_layover_minutes, avoid_airports, max_layover_minutes)

    passing = [o for o in offers if ok(o)]
    discarded_unknown = sum(1 for o in offers if _has_unknown_duration(o) and not ok(o))
    best = min(passing, key=lambda o: o.total_price_brl, default=None)
    return best, discarded_unknown

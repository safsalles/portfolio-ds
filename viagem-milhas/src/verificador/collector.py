import json
from dataclasses import dataclass

import requests

from verificador.config import Config
from verificador.models import Layover, Leg, Offer
from verificador.rules import leg_is_compliant

SEARCH_URL = "https://serpapi.com/search.json"
MAX_EXPAND = 3  # idas candidatas expandidas por dia (1 + 3 = ate 4 consultas/dia)
_NO_RESULTS = "hasn't returned any results"
_TRAVEL_CLASS = {"economy": "1", "premium_economy": "2", "business": "3", "first": "4"}


class CollectorError(Exception):
    """Falha ao consultar a API (HTTP, cota, rede). Nunca inclui a chave."""


@dataclass(frozen=True)
class LegOption:
    total_price_brl: float
    leg: Leg
    departure_token: str | None


def parse_leg_options(payload: dict) -> list[LegOption]:
    options: list[LegOption] = []
    for group in ("best_flights", "other_flights"):
        for item in payload.get(group, []):
            flights = item.get("flights") or []
            if not flights or item.get("price") is None:
                continue
            airlines = tuple(dict.fromkeys(f.get("airline", "") for f in flights))
            layovers = tuple(Layover(l.get("id", "?"), l.get("duration")) for l in item.get("layovers", []))
            leg = Leg(
                flights[0]["departure_airport"]["id"],
                flights[-1]["arrival_airport"]["id"],
                airlines,
                layovers,
            )
            options.append(LegOption(float(item["price"]), leg, item.get("departure_token")))
    return options


def _call(get, params: dict) -> dict:
    try:
        resp = get(SEARCH_URL, params=params, timeout=60)
    except requests.RequestException as exc:
        raise CollectorError(f"falha de rede ({type(exc).__name__})") from None
    if resp.status_code >= 400:
        raise CollectorError(f"HTTP {resp.status_code}")
    payload = resp.json()
    error = payload.get("error")
    if error:
        if _NO_RESULTS in error:
            return {}
        raise CollectorError(str(error))
    return payload


def fetch_offers(cfg: Config, api_key: str, max_expand: int = MAX_EXPAND, get=requests.get) -> list[Offer]:
    out_from, out_to, out_date = cfg.trip.outbound
    in_from, in_to, in_date = cfg.trip.inbound
    params = {
        "engine": "google_flights",
        "type": "3",
        "multi_city_json": json.dumps(
            [
                {"departure_id": out_from, "arrival_id": out_to, "date": out_date},
                {"departure_id": in_from, "arrival_id": in_to, "date": in_date},
            ]
        ),
        "adults": str(cfg.trip.adults),
        "currency": cfg.trip.currency,
        "hl": "pt",
        "gl": "br",
        "travel_class": _TRAVEL_CLASS.get(cfg.trip.cabin, "1"),
        "api_key": api_key,
    }
    if cfg.baggage.send_to_api and cfg.baggage.carry_on > 0:
        params["bags"] = str(cfg.baggage.carry_on)
    outbound_options = parse_leg_options(_call(get, params))
    rules = cfg.rules
    candidates = sorted(
        (
            o
            for o in outbound_options
            if o.departure_token and leg_is_compliant(o.leg, rules.min_layover_minutes, rules.avoid_airports)
        ),
        key=lambda o: o.total_price_brl,
    )[:max_expand]

    offers: list[Offer] = []
    for outbound in candidates:
        payload = _call(get, {**params, "departure_token": outbound.departure_token})
        for inbound in parse_leg_options(payload):
            offers.append(Offer(inbound.total_price_brl, outbound.leg, inbound.leg, None))
    return offers



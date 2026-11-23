import json
from dataclasses import replace
from pathlib import Path

import pytest

from verificador.collector import CollectorError, fetch_offers, parse_leg_options
from verificador.config import Baggage, load_config
from verificador.models import Layover

FIXTURES = Path(__file__).parent / "fixtures"
CONFIG = "tests/fixtures/config_test.toml"
LEG1 = json.loads((FIXTURES / "serpapi_open_jaw.json").read_text(encoding="utf-8"))
LEG2 = json.loads((FIXTURES / "serpapi_open_jaw_leg2.json").read_text(encoding="utf-8"))


class FakeResp:
    def __init__(self, payload, status=200):
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def make_get(first=LEG1, second=LEG2, status=200):
    calls = []

    def get(url, params, timeout):
        calls.append(dict(params))
        payload = second if "departure_token" in params else first
        return FakeResp(payload, status)

    return get, calls


def test_parse_outbound_options_from_fixture():
    options = parse_leg_options(LEG1)

    assert len(options) == 9
    first = options[0]
    assert first.total_price_brl == 19400
    assert first.leg.origin == "GIG" and first.leg.destination == "BUD"
    assert first.leg.airlines == ("KLM",)
    assert first.leg.layovers == (Layover("AMS", 420),)
    assert first.departure_token


def test_parse_inbound_options_from_fixture():
    options = parse_leg_options(LEG2)

    assert len(options) == 4
    assert options[0].leg.origin == "BER" and options[0].leg.destination == "GIG"
    assert options[0].total_price_brl == 19400
    assert options[0].leg.layovers == (Layover("AMS", 140),)
    assert options[0].departure_token is None


def test_parse_empty_payload_returns_empty_list():
    assert parse_leg_options({}) == []


def test_missing_layover_duration_becomes_none():
    payload = json.loads(json.dumps(LEG2))
    del payload["other_flights"][0]["layovers"][0]["duration"]

    assert parse_leg_options(payload)[0].leg.layovers[0].minutes is None


def test_fetch_expands_only_cheapest_compliant_outbounds():
    cfg = load_config(CONFIG)
    get, calls = make_get()

    offers = fetch_offers(cfg, "chave-falsa", max_expand=2, get=get)

    expansions = [c for c in calls if "departure_token" in c]
    assert len(calls) == 3 and len(expansions) == 2
    outbound = parse_leg_options(LEG1)
    reprovada_cdg_85 = next(o for o in outbound if o.leg.layovers and o.leg.layovers[0].minutes == 85)
    assert reprovada_cdg_85.departure_token not in [c["departure_token"] for c in expansions]
    assert len(offers) == 8  # 2 idas x 4 voltas
    assert all(o.outbound.origin == "GIG" and o.inbound.origin == "BER" for o in offers)
    assert {o.outbound.layovers[0].airport for o in offers} <= {"AMS", "FCO"}


def test_fetch_sends_trip_from_config_and_key_as_param():
    cfg = load_config(CONFIG)
    get, calls = make_get()

    fetch_offers(cfg, "chave-falsa", max_expand=1, get=get)

    first = calls[0]
    assert first["api_key"] == "chave-falsa"
    assert first["adults"] == "2" and first["currency"] == "BRL" and first["type"] == "3"
    legs = json.loads(first["multi_city_json"])
    assert legs[0] == {"departure_id": "GIG", "arrival_id": "BUD", "date": "2027-07-10"}
    assert legs[1] == {"departure_id": "BER", "arrival_id": "GIG", "date": "2027-07-22"}


def test_fetch_raises_on_api_error_field():
    cfg = load_config(CONFIG)
    get, _ = make_get(first={"error": "Your account has run out of searches."})

    with pytest.raises(CollectorError, match="run out of searches"):
        fetch_offers(cfg, "chave-falsa", get=get)


def test_fetch_raises_on_http_error():
    cfg = load_config(CONFIG)
    get, _ = make_get(first={}, status=429)

    with pytest.raises(CollectorError, match="429"):
        fetch_offers(cfg, "chave-falsa", get=get)


def test_fetch_no_results_error_is_empty_list():
    cfg = load_config(CONFIG)
    get, _ = make_get(first={"error": "Google Flights hasn't returned any results for this query."})

    assert fetch_offers(cfg, "chave-falsa", get=get) == []




def test_fetch_sends_carry_on_bags_only_when_opted_in():
    cfg = replace(load_config(CONFIG), baggage=Baggage(2, 1, 600.0, send_to_api=True))
    get, calls = make_get()

    fetch_offers(cfg, "chave-falsa", max_expand=1, get=get)

    assert calls[0]["bags"] == "2"


def test_fetch_does_not_send_bags_by_default():
    # O filtro de malas da API esconde ofertas validas (testado ao vivo), entao fica desligado por padrao.
    cfg = load_config(CONFIG)
    get, calls = make_get()

    fetch_offers(cfg, "chave-falsa", max_expand=1, get=get)

    assert "bags" not in calls[0]


def test_fetch_omits_bags_when_opted_in_but_no_carry_on():
    cfg = replace(load_config(CONFIG), baggage=Baggage(0, 1, 600.0, send_to_api=True))
    get, calls = make_get()

    fetch_offers(cfg, "chave-falsa", max_expand=1, get=get)

    assert "bags" not in calls[0]
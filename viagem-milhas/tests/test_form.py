from datetime import date

from verificador.config import load_config
from verificador.setup import build_config_toml, form_defaults, parse_form

TODAY = date(2026, 11, 23)
CONFIG = "tests/fixtures/config_test.toml"

VALID = {
    "origin": "gru", "dest": "lis", "out_date": "2027-03-10",
    "back_from": "", "back_to": "", "back_date": "2027-03-24",
    "adults": "2", "cabin": "", "carry_on": "1", "checked": "1", "fee": "500",
    "hours": "4", "max_hours": "", "avoid": "", "currency": "BRL", "drop": "", "target": "18000",
}


def test_parse_form_valid_values():
    values, errors = parse_form(VALID, TODAY)

    assert errors == {}
    assert values["outbound"] == ["GRU", "LIS", "2027-03-10"]
    assert values["inbound"] == ["LIS", "GRU", "2027-03-24"]  # volta = ida invertida por padrao
    assert values["adults"] == 2 and values["cabin"] == "economy"
    assert values["min_layover_minutes"] == 240
    assert values["carry_on"] == 1 and values["checked"] == 1 and values["checked_bag_fee_brl"] == 500.0
    assert values["drop_pct"] == 5.0 and values["target_brl"] == 18000.0


def test_parse_form_values_build_a_loadable_config(tmp_path):
    values, _ = parse_form(VALID, TODAY)
    path = tmp_path / "config.toml"
    path.write_text(build_config_toml(values), encoding="utf-8")

    cfg = load_config(str(path))

    assert cfg.trip.outbound == ("GRU", "LIS", "2027-03-10")
    assert cfg.baggage.checked == 1


def test_parse_form_collects_all_errors_at_once():
    raw = dict(VALID, origin="XX1", out_date="2020-01-01", adults="0")

    values, errors = parse_form(raw, TODAY)

    assert values is None
    assert set(errors) == {"origin", "out_date", "adults"}
    assert "3 letras" in errors["origin"] and "passado" in errors["out_date"]


def test_parse_form_return_must_not_be_before_outbound():
    values, errors = parse_form(dict(VALID, back_date="2027-03-05"), TODAY)

    assert values is None and set(errors) == {"back_date"}
    assert "depois da ida" in errors["back_date"]


def test_parse_form_skips_fee_when_no_checked_bags():
    values, errors = parse_form(dict(VALID, checked="0", fee="abc"), TODAY)

    assert errors == {} and values["checked_bag_fee_brl"] == 0.0


def test_form_defaults_from_existing_config():
    d = form_defaults(load_config(CONFIG))

    assert d["origin"] == "GIG" and d["dest"] == "BUD" and d["out_date"] == "2027-07-10"
    assert d["back_from"] == "BER" and d["back_to"] == "GIG" and d["back_date"] == "2027-07-22"
    assert d["adults"] == "2" and d["cabin"] == "economy"
    assert d["carry_on"] == "2" and d["checked"] == "1" and d["fee"] == "600"
    assert d["hours"] == "4" and d["max_hours"] == "0" and d["avoid"] == "" and d["currency"] == "BRL"
    assert d["drop"] == "5" and d["target"] == "18000"


def test_form_defaults_without_config_are_blank_or_sensible():
    d = form_defaults(None)

    assert d["origin"] == "" and d["adults"] == "1" and d["cabin"] == "economy" and d["currency"] == "BRL"


def test_parse_form_maximum_layover():
    values, errors = parse_form(dict(VALID, max_hours="8"), TODAY)

    assert errors == {} and values["max_layover_minutes"] == 480
    assert parse_form(VALID, TODAY)[0]["max_layover_minutes"] == 0  # em branco = sem limite


def test_parse_form_maximum_must_exceed_minimum():
    values, errors = parse_form(dict(VALID, hours="4", max_hours="3"), TODAY)

    assert values is None and "maior" in errors["max_hours"]


def test_build_config_toml_writes_the_maximum(tmp_path):
    values, _ = parse_form(dict(VALID, max_hours="8"), TODAY)
    path = tmp_path / "config.toml"
    path.write_text(build_config_toml(values), encoding="utf-8")

    assert load_config(str(path)).rules.max_layover_minutes == 480

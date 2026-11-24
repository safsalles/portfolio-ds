from datetime import date

from verificador.config import load_config
from verificador.setup import build_config_toml, form_defaults, merge_existing, parse_form

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


def test_parse_form_accepts_several_airports_of_the_same_city():
    values, errors = parse_form(dict(VALID, origin="gig, sdu", dest="lhr,lgw"), TODAY)

    assert errors == {}
    assert values["outbound"][:2] == ["GIG,SDU", "LHR,LGW"]
    assert values["inbound"][:2] == ["LHR,LGW", "GIG,SDU"]  # a volta inverte as listas inteiras


def test_parse_form_unknown_place_explains_how_to_fix_it():
    values, errors = parse_form(dict(VALID, origin="Atlantida"), TODAY)

    assert values is None
    assert "Não achei esse lugar" in errors["origin"] and "3 letras" in errors["origin"]


def _custom_config(tmp_path):
    text = open(CONFIG, encoding="utf-8").read()
    text = text.replace('history = "data/history.csv"', 'history = "meu/hist.csv"\nsnapshots = "meu/consultas"')
    text = text.replace('"smiles" = 12', '"smiles" = 9').replace("checked_bag_fee_brl = 600", "checked_bag_fee_brl = 600\nsend_to_api = true")
    path = tmp_path / "personalizada.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_saving_keeps_paths_promos_and_send_to_api_from_the_existing_config(tmp_path):
    existing = load_config(str(_custom_config(tmp_path)))
    values, _ = parse_form(VALID, TODAY)

    out = tmp_path / "salva.toml"
    out.write_text(build_config_toml(merge_existing(values, existing)), encoding="utf-8")
    saved = load_config(str(out))

    assert saved.trip.outbound[0] == "GRU"  # o que veio do formulario vale
    assert saved.paths.history == "meu/hist.csv" and saved.paths.snapshots == "meu/consultas"
    assert saved.promos.max_milheiro["smiles"] == 9.0
    assert saved.promos.feeds == ("https://exemplo.test/feed/",)
    assert saved.baggage.send_to_api is True


def test_without_an_existing_config_the_defaults_are_written(tmp_path):
    values, _ = parse_form(VALID, TODAY)
    out = tmp_path / "nova.toml"
    out.write_text(build_config_toml(values), encoding="utf-8")
    saved = load_config(str(out))

    assert saved.paths.history == "data/history.csv" and saved.paths.snapshots == "data/snapshots"
    assert saved.promos.max_milheiro["smiles"] == 12.0 and saved.baggage.send_to_api is False

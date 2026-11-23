from verificador.config import Baggage, load_config

CONFIG = "tests/fixtures/config_test.toml"


def test_load_config_has_expected_values():
    cfg = load_config(CONFIG)

    assert cfg.trip.outbound == ("GIG", "BUD", "2027-07-10")
    assert cfg.trip.inbound == ("BER", "GIG", "2027-07-22")
    assert cfg.trip.adults == 2
    assert cfg.rules.min_layover_minutes == 240
    assert cfg.rules.avoid_airports == frozenset()
    assert cfg.alerts.drop_pct == 5.0
    assert cfg.alerts.target_brl == 18000
    assert cfg.promos.max_milheiro["smiles"] == 12


def test_baggage_values_come_from_config():
    cfg = load_config(CONFIG)

    assert cfg.baggage == Baggage(carry_on=2, checked=1, checked_bag_fee_brl=600.0)


def test_baggage_section_is_optional_with_zero_defaults(tmp_path):
    text = open(CONFIG, encoding="utf-8").read().split("[baggage]")[0]
    path = tmp_path / "sem_bagagem.toml"
    path.write_text(text, encoding="utf-8")

    cfg = load_config(str(path))

    assert cfg.baggage == Baggage(carry_on=0, checked=0, checked_bag_fee_brl=0.0)


def test_avoid_airports_is_read_as_a_set(tmp_path):
    text = open(CONFIG, encoding="utf-8").read().replace("avoid_airports = []", 'avoid_airports = ["GRU", "VCP"]')
    path = tmp_path / "evitar.toml"
    path.write_text(text, encoding="utf-8")

    assert load_config(str(path)).rules.avoid_airports == frozenset({"GRU", "VCP"})


def test_config_saved_with_utf8_bom_still_loads(tmp_path):
    # O Bloco de Notas e o PowerShell 5 gravam UTF-8 com BOM; a configuracao nao pode quebrar por isso.
    text = open(CONFIG, encoding="utf-8").read()
    path = tmp_path / "com_bom.toml"
    path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))

    assert load_config(str(path)).trip.adults == 2


def test_send_to_api_defaults_to_false_and_can_be_enabled(tmp_path):
    assert load_config(CONFIG).baggage.send_to_api is False
    text = open(CONFIG, encoding="utf-8").read().replace("checked_bag_fee_brl = 600", "checked_bag_fee_brl = 600\nsend_to_api = true")
    path = tmp_path / "api.toml"
    path.write_text(text, encoding="utf-8")

    assert load_config(str(path)).baggage.send_to_api is True

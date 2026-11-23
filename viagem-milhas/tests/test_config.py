from verificador.config import load_config


def test_load_config_has_spec_values():
    cfg = load_config("config.toml")

    assert cfg.trip.outbound == ("GIG", "BUD", "2027-07-10")
    assert cfg.trip.inbound == ("BER", "GIG", "2027-07-22")
    assert cfg.trip.adults == 2
    assert cfg.rules.min_layover_minutes == 240
    assert cfg.rules.brazil_airports == frozenset()  # regra do Brasil removida: nunca foi pedido pelo Sergio
    assert cfg.alerts.drop_pct == 5.0
    assert cfg.alerts.target_brl == 18000
    assert cfg.promos.max_milheiro["smiles"] == 12


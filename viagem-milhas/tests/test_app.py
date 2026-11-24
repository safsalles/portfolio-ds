from datetime import date, timedelta
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from verificador.config import load_config  # noqa: E402
from verificador.models import Layover, Leg, Offer  # noqa: E402
from verificador.snapshots import list_snapshots  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "src" / "verificador" / "app.py")
CONFIG = "tests/fixtures/config_test.toml"


def make_config(tmp_path):
    """Copia a configuracao de teste apontando os dados para a pasta temporaria."""
    text = open(CONFIG, encoding="utf-8").read()
    for name in ("history.csv", "seen_promos.json", "alerts.log"):
        text = text.replace(f'"data/{name}"', f'"{(tmp_path / name).as_posix()}"')
    text = text.replace(f'alerts_log = "{(tmp_path / "alerts.log").as_posix()}"',
                        f'alerts_log = "{(tmp_path / "alerts.log").as_posix()}"\nsnapshots = "{(tmp_path / "snaps").as_posix()}"')
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    return path


def run_app(monkeypatch, config_path):
    monkeypatch.setenv("VERIFICADOR_CONFIG", str(config_path))
    return AppTest.from_file(APP, default_timeout=60).run()


def test_app_opens_without_config_and_shows_an_empty_form(monkeypatch, tmp_path):
    at = run_app(monkeypatch, tmp_path / "nao_existe.toml")

    assert not at.exception
    assert at.text_input(key="f_origin").value == ""
    assert at.number_input(key="f_adults").value == 1


def test_app_prefills_the_form_from_the_existing_config(monkeypatch, tmp_path):
    at = run_app(monkeypatch, make_config(tmp_path))

    assert not at.exception
    assert at.text_input(key="f_origin").value == "GIG"
    assert at.text_input(key="f_dest").value == "BUD"
    assert at.number_input(key="f_checked").value == 1


def test_app_saves_a_valid_trip_to_config(monkeypatch, tmp_path):
    path = tmp_path / "nova.toml"
    at = run_app(monkeypatch, path)
    soon = date.today() + timedelta(days=60)
    at.text_input(key="f_origin").set_value("gru")
    at.text_input(key="f_dest").set_value("lis")
    at.date_input(key="f_out_date").set_value(soon)
    at.date_input(key="f_back_date").set_value(soon + timedelta(days=14))
    at.number_input(key="f_adults").set_value(2)

    next(b for b in at.button if b.label == "Salvar viagem").click()
    at.run()

    assert not at.exception
    cfg = load_config(str(path))
    assert cfg.trip.outbound == ("GRU", "LIS", soon.isoformat())
    assert cfg.trip.inbound[:2] == ("LIS", "GRU")
    assert cfg.trip.adults == 2


def test_app_shows_errors_and_does_not_save_an_invalid_trip(monkeypatch, tmp_path):
    path = tmp_path / "nova.toml"
    at = run_app(monkeypatch, path)
    at.text_input(key="f_origin").set_value("XX1")
    at.text_input(key="f_dest").set_value("lis")

    next(b for b in at.button if b.label == "Salvar viagem").click()
    at.run()

    assert not at.exception
    assert not path.exists()
    assert any("3 letras" in e.value for e in at.error)


def test_consult_now_runs_the_search_and_saves_the_whole_consultation(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    offers = [
        Offer(19152.0, Leg("GIG", "BUD", ("KLM",), (Layover("AMS", 420),)), Leg("BER", "GIG", ("KLM",), (Layover("AMS", 325),)), None),
        Offer(17243.0, Leg("GIG", "BUD", ("TK",), (Layover("IST", 65),)), Leg("BER", "GIG", ("TK",), (Layover("IST", 195),)), None),
    ]
    monkeypatch.setattr("verificador.collector.fetch_offers", lambda cfg, key: offers)
    monkeypatch.setenv("SERPAPI_KEY", "chave-falsa")
    at = run_app(monkeypatch, config)

    next(b for b in at.button if b.label == "Consultar agora").click()
    at.run()

    assert not at.exception
    metas = list_snapshots(str(tmp_path / "snaps"))
    assert len(metas) == 1 and metas[0].source == "manual" and metas[0].best_total_brl == 19152.0 and metas[0].n_offers == 2


def test_consult_now_without_api_key_explains_instead_of_crashing(monkeypatch, tmp_path):
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    at = run_app(monkeypatch, make_config(tmp_path))

    next(b for b in at.button if b.label == "Consultar agora").click()
    at.run()

    assert not at.exception
    assert any("SERPAPI_KEY" in e.value for e in at.error)
    assert list_snapshots(str(tmp_path / "snaps")) == []


def test_app_saves_the_maximum_layover_from_the_form(monkeypatch, tmp_path):
    path = tmp_path / "nova.toml"
    at = run_app(monkeypatch, path)
    soon = date.today() + timedelta(days=60)
    at.text_input(key="f_origin").set_value("gru")
    at.text_input(key="f_dest").set_value("lis")
    at.date_input(key="f_out_date").set_value(soon)
    at.date_input(key="f_back_date").set_value(soon + timedelta(days=14))
    at.number_input(key="f_hours").set_value(4.0)
    at.number_input(key="f_max_hours").set_value(8.0)

    next(b for b in at.button if b.label == "Salvar viagem").click()
    at.run()

    assert not at.exception
    rules = load_config(str(path)).rules
    assert rules.min_layover_minutes == 240 and rules.max_layover_minutes == 480


def test_typing_a_city_name_offers_the_matching_places(monkeypatch, tmp_path):
    at = run_app(monkeypatch, tmp_path / "nova.toml")

    at.text_input(key="f_dest").set_value("Lisboa")
    at.run()

    assert not at.exception
    assert at.selectbox(key="f_dest_pick").value == "LIS"  # a primeira opcao e' Lisboa
    assert any("Lisboa" in c.value for c in at.caption)


def test_unknown_place_says_it_was_not_found(monkeypatch, tmp_path):
    at = run_app(monkeypatch, tmp_path / "nova.toml")

    at.text_input(key="f_dest").set_value("Atlantida")
    at.run()

    assert not at.exception
    assert any("Não achei esse lugar" in c.value for c in at.caption)


def test_app_saves_a_trip_typed_with_city_names(monkeypatch, tmp_path):
    path = tmp_path / "nova.toml"
    at = run_app(monkeypatch, path)
    soon = date.today() + timedelta(days=60)
    at.text_input(key="f_origin").set_value("Rio de Janeiro")
    at.text_input(key="f_dest").set_value("Lisboa")
    at.date_input(key="f_out_date").set_value(soon)
    at.date_input(key="f_back_date").set_value(soon + timedelta(days=14))
    at.run()  # recarrega para os seletores de lugar aparecerem

    next(b for b in at.button if b.label == "Salvar viagem").click()
    at.run()

    assert not at.exception
    trip = load_config(str(path)).trip
    assert trip.outbound[:2] == ("GIG,SDU", "LIS")  # cidade com 2 aeroportos entra com os dois
    assert trip.inbound[:2] == ("LIS", "GIG,SDU")


def test_save_and_consult_saves_the_trip_and_runs_the_search(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    offers = [
        Offer(19152.0, Leg("GIG", "BUD", ("KLM",), (Layover("AMS", 420),)), Leg("BER", "GIG", ("KLM",), (Layover("AMS", 325),)), None),
    ]
    monkeypatch.setattr("verificador.collector.fetch_offers", lambda cfg, key: offers)
    monkeypatch.setenv("SERPAPI_KEY", "chave-falsa")
    at = run_app(monkeypatch, config)
    at.number_input(key="f_adults").set_value(3)

    next(b for b in at.button if b.label == "Salvar e consultar agora").click()
    at.run()

    assert not at.exception
    assert load_config(str(config)).trip.adults == 3
    metas = list_snapshots(str(tmp_path / "snaps"))
    assert len(metas) == 1 and metas[0].source == "manual" and metas[0].best_total_brl == 19152.0


def test_save_and_consult_without_api_key_saves_the_trip_but_explains(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    at = run_app(monkeypatch, config)
    at.number_input(key="f_adults").set_value(3)

    next(b for b in at.button if b.label == "Salvar e consultar agora").click()
    at.run()

    assert not at.exception
    assert load_config(str(config)).trip.adults == 3
    assert any("SERPAPI_KEY" in e.value for e in at.error)
    assert list_snapshots(str(tmp_path / "snaps")) == []


def test_miles_tab_shows_the_breakeven_and_verdict_for_a_manual_price(monkeypatch, tmp_path):
    at = run_app(monkeypatch, make_config(tmp_path))
    at.number_input(key="m_cash").set_value(20000.0)
    at.number_input(key="m_miles").set_value(100000)
    at.number_input(key="m_seen").set_value(15.0)
    at.run()

    assert not at.exception
    assert any("200,00" in m.value or "200.00" in m.value for m in at.metric)  # 20000/100 = R$ 200 por milheiro
    assert any("Compensa nesta viagem" in m.value for m in at.markdown)

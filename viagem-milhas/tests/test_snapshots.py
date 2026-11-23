from datetime import datetime

from verificador.config import load_config
from verificador.models import Layover, Leg, Offer
from verificador.snapshots import (
    compare_best,
    describe_layovers,
    list_snapshots,
    load_snapshot,
    offer_rows,
    save_snapshot,
)

CONFIG = "tests/fixtures/config_test.toml"


def offer(price, out_min=420, in_min=325, in_airport="AMS"):
    outbound = Leg("GIG", "BUD", ("KLM",), (Layover("AMS", out_min),))
    inbound = Leg("BER", "GIG", ("KLM",), (Layover(in_airport, in_min),))
    return Offer(price, outbound, inbound, None)


def test_save_and_load_roundtrip(tmp_path):
    cfg = load_config(CONFIG)
    offers = [offer(19152), offer(17243, in_min=130)]  # a 2a reprova a regra das 4h

    path = save_snapshot(str(tmp_path), cfg, offers, source="manual", now=datetime(2026, 11, 23, 15, 33, 0))

    assert path.endswith("2026-11-23_15-33-00.json")
    snap = load_snapshot(path)
    assert snap["source"] == "manual"
    assert snap["trip"]["outbound"] == ["GIG", "BUD", "2027-07-10"]
    assert [o["total_price_brl"] for o in snap["offers"]] == [17243.0, 19152.0]  # do mais barato ao mais caro
    assert [o["compliant"] for o in snap["offers"]] == [False, True]
    assert snap["best_total_brl"] == 19152.0  # o mais barato que passa nas regras


def test_snapshot_with_no_compliant_offer_has_no_best(tmp_path):
    cfg = load_config(CONFIG)

    path = save_snapshot(str(tmp_path), cfg, [offer(17243, in_min=130)], "agendada", datetime(2026, 11, 23, 8, 0, 0))

    assert load_snapshot(path)["best_total_brl"] is None


def test_two_saves_in_the_same_second_do_not_overwrite(tmp_path):
    cfg = load_config(CONFIG)
    now = datetime(2026, 11, 23, 8, 0, 0)

    a = save_snapshot(str(tmp_path), cfg, [offer(19152)], "agendada", now)
    b = save_snapshot(str(tmp_path), cfg, [offer(18000)], "manual", now)

    assert a != b
    assert len(list_snapshots(str(tmp_path))) == 2


def test_list_snapshots_newest_first(tmp_path):
    cfg = load_config(CONFIG)
    save_snapshot(str(tmp_path), cfg, [offer(19500)], "agendada", datetime(2026, 11, 22, 8, 0, 0))
    save_snapshot(str(tmp_path), cfg, [offer(19152)], "agendada", datetime(2026, 11, 23, 8, 0, 0))
    save_snapshot(str(tmp_path), cfg, [offer(19000)], "manual", datetime(2026, 11, 23, 18, 0, 0))

    metas = list_snapshots(str(tmp_path))

    assert [m.best_total_brl for m in metas] == [19000.0, 19152.0, 19500.0]
    assert metas[0].saved_at == datetime(2026, 11, 23, 18, 0, 0)
    assert metas[0].source == "manual" and metas[0].n_offers == 1


def test_list_snapshots_missing_dir_is_empty(tmp_path):
    assert list_snapshots(str(tmp_path / "nao_existe")) == []


def test_offer_rows_are_flat_sorted_and_flag_compliance(tmp_path):
    cfg = load_config(CONFIG)
    path = save_snapshot(str(tmp_path), cfg, [offer(19152), offer(17243, in_min=130)], "manual", datetime(2026, 11, 23, 15, 0, 0))

    rows = offer_rows(load_snapshot(path))

    assert rows[0]["Total (R$)"] == 17243.0 and rows[0]["Passa nas regras"] == "Não"
    assert rows[1]["Total (R$)"] == 19152.0 and rows[1]["Passa nas regras"] == "Sim"
    assert rows[1]["Companhias"] == "KLM"
    assert rows[1]["Escalas da ida"] == "AMS 7h00" and rows[1]["Escalas da volta"] == "AMS 5h25"


def test_describe_layovers():
    assert describe_layovers([]) == "direto"
    assert describe_layovers([{"airport": "AMS", "minutes": 420}, {"airport": "CDG", "minutes": None}]) == "AMS 7h00 + CDG ?"


def test_compare_best():
    assert compare_best(18900.0, 19152.0) == (-252.0, -252.0 / 19152.0 * 100)
    assert compare_best(None, 19152.0) is None
    assert compare_best(18900.0, None) is None

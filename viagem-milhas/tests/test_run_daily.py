import csv
from dataclasses import replace

from verificador.collector import CollectorError
from verificador.config import Paths, load_config
from verificador.history import HistoryRecord, upsert_record
from verificador.models import Layover, Leg, Offer
from verificador.run_daily import main, run
from verificador.snapshots import list_snapshots


CONFIG = "tests/fixtures/config_test.toml"


def make_cfg(tmp_path):
    cfg = load_config(CONFIG)
    paths = Paths(
        history=str(tmp_path / "history.csv"),
        seen_promos=str(tmp_path / "seen.json"),
        alerts_log=str(tmp_path / "alerts.log"),
        snapshots=str(tmp_path / "snaps"),
    )
    return replace(cfg, paths=paths)


def offer(price, out_min=420, in_min=325, in_airport="AMS"):
    outbound = Leg("GIG", "BUD", ("KLM",), (Layover("AMS", out_min),))
    inbound = Leg("BER", "GIG", ("KLM",), (Layover(in_airport, in_min),))
    return Offer(price, outbound, inbound, None)


class Notes:
    def __init__(self):
        self.calls = []

    def __call__(self, title, message, log_path):
        self.calls.append((title, message))


def no_feeds(url):
    return []


def rows(cfg):
    with open(cfg.paths.history, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_run_records_cheapest_compliant_and_returns_0(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()
    offers = [offer(17243, in_min=130, in_airport="GRU"), offer(19152), offer(20000)]

    code = run(cfg, "k", "2026-11-23", fetch=lambda c, k: offers, notify_fn=notes, feed_fn=no_feeds)

    assert code == 0
    only = rows(cfg)
    assert len(only) == 1 and only[0]["status"] == "ok" and only[0]["total_price_brl"] == "19152.0"


def test_run_empty_offers_records_status_empty_and_notifies_failure(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()

    code = run(cfg, "k", "2026-11-23", fetch=lambda c, k: [], notify_fn=notes, feed_fn=no_feeds)

    assert code == 1
    only = rows(cfg)
    assert only[0]["status"] == "empty" and only[0]["total_price_brl"] == ""
    assert len(notes.calls) == 1 and "nenhuma oferta" in notes.calls[0][0].lower()


def test_run_no_compliant_offer_mentions_unknown_duration(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()
    unknown = Offer(15000, Leg("GIG", "BUD", ("KLM",), (Layover("AMS", None),)), Leg("BER", "GIG", ("KLM",), ()), None)

    code = run(cfg, "k", "2026-11-23", fetch=lambda c, k: [unknown], notify_fn=notes, feed_fn=no_feeds)

    assert code == 1
    assert "sem dura" in notes.calls[0][1].lower()


def test_run_fetch_error_records_status_error_and_notifies(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()

    def boom(c, k):
        raise CollectorError("HTTP 429")

    code = run(cfg, "k", "2026-11-23", fetch=boom, notify_fn=notes, feed_fn=no_feeds)

    assert code == 1
    assert rows(cfg)[0]["status"] == "error"
    assert "429" in notes.calls[0][1]


def test_run_twice_same_day_single_row_and_no_duplicate_alert(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()
    below_target = [offer(17900)]

    run(cfg, "k", "2026-11-23", fetch=lambda c, k: below_target, notify_fn=notes, feed_fn=no_feeds)
    after_first = len(notes.calls)
    run(cfg, "k", "2026-11-23", fetch=lambda c, k: below_target, notify_fn=notes, feed_fn=no_feeds)

    assert after_first == 1
    assert len(notes.calls) == after_first
    assert len(rows(cfg)) == 1


def test_run_first_run_no_drop_alert(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()

    run(cfg, "k", "2026-11-23", fetch=lambda c, k: [offer(19152)], notify_fn=notes, feed_fn=no_feeds)

    assert notes.calls == []


def test_run_alerts_on_drop_against_previous_day(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()
    upsert_record(cfg.paths.history, HistoryRecord("2026-11-22", 20000.0, "KLM", "AMS 7h00", None, "ok"))

    run(cfg, "k", "2026-11-23", fetch=lambda c, k: [offer(18900)], notify_fn=notes, feed_fn=no_feeds)

    assert len(notes.calls) == 1 and "caiu" in notes.calls[0][1].lower()


def test_run_notifies_promos_once(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()
    promo = [{"title": "Flying Blue: milheiro a R$ 29", "summary": "", "link": "https://exemplo.test/p"}]

    run(cfg, "k", "2026-11-23", fetch=lambda c, k: [offer(19152)], notify_fn=notes, feed_fn=lambda u: promo)
    first = len(notes.calls)
    run(cfg, "k", "2026-11-24", fetch=lambda c, k: [offer(19152)], notify_fn=notes, feed_fn=lambda u: promo)

    assert first >= 1
    assert len(notes.calls) == first


def test_run_feed_failure_does_not_break_the_run(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()

    def bad_feed(url):
        raise OSError("feed fora do ar")

    code = run(cfg, "k", "2026-11-23", fetch=lambda c, k: [offer(19152)], notify_fn=notes, feed_fn=bad_feed)

    assert code == 0
    assert rows(cfg)[0]["status"] == "ok"


def test_main_without_api_key_returns_1(monkeypatch):
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    notes = Notes()

    assert main(notify_fn=notes, config_path=CONFIG) == 1
    assert len(notes.calls) == 1 and "serpapi_key" in notes.calls[0][1].lower()


def test_failed_rerun_does_not_overwrite_good_record_of_the_day(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()
    run(cfg, "k", "2026-11-23", fetch=lambda c, k: [offer(19152)], notify_fn=notes, feed_fn=no_feeds)

    def boom(c, k):
        raise CollectorError("HTTP 429")

    code = run(cfg, "k", "2026-11-23", fetch=boom, notify_fn=notes, feed_fn=no_feeds)

    assert code == 1
    only = rows(cfg)
    assert len(only) == 1 and only[0]["status"] == "ok" and only[0]["total_price_brl"] == "19152.0"
    assert "429" in notes.calls[-1][1]





def test_main_without_config_file_points_to_setup(tmp_path):
    notes = Notes()

    code = main(notify_fn=notes, config_path=str(tmp_path / "nao_existe.toml"))

    assert code == 1
    assert len(notes.calls) == 1 and "verificador.setup" in notes.calls[0][1]


def test_run_saves_snapshot_of_all_offers_even_when_none_pass(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()

    run(cfg, "k", "2026-11-23", fetch=lambda c, k: [offer(17243, in_min=130)], notify_fn=notes, feed_fn=no_feeds)

    metas = list_snapshots(cfg.paths.snapshots)
    assert len(metas) == 1
    assert metas[0].source == "agendada" and metas[0].n_offers == 1 and metas[0].best_total_brl is None


def test_run_saves_snapshot_with_best_compliant_price(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()

    run(cfg, "k", "2026-11-23", fetch=lambda c, k: [offer(19152), offer(20000)], notify_fn=notes, feed_fn=no_feeds)

    metas = list_snapshots(cfg.paths.snapshots)
    assert len(metas) == 1 and metas[0].best_total_brl == 19152.0 and metas[0].n_offers == 2


def test_run_does_not_save_snapshot_when_fetch_fails(tmp_path):
    cfg, notes = make_cfg(tmp_path), Notes()

    def boom(c, k):
        raise CollectorError("HTTP 429")

    run(cfg, "k", "2026-11-23", fetch=boom, notify_fn=notes, feed_fn=no_feeds)

    assert list_snapshots(cfg.paths.snapshots) == []

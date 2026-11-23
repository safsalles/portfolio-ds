from verificador.history import HistoryRecord, upsert_record
from verificador.other_sources import OtherCheck, append_check
from verificador.report import build_report


def test_report_shows_google_and_other_sources_and_breakeven(tmp_path):
    hist = str(tmp_path / "history.csv")
    others = str(tmp_path / "outras.csv")
    upsert_record(hist, HistoryRecord("2026-11-23", 21440.0, "KLM+Air France", "AMS 7h00", None, "ok"))
    append_check(others, OtherCheck("2026-11-23", "kayak", 19152.0, None, None, "KLM Light"))
    append_check(others, OtherCheck("2026-11-23", "flying blue", None, 502000, 3000.0, "ida+volta"))

    text = build_report(hist, others)

    assert "Google Voos" in text and "21,440.00" in text
    assert "kayak" in text and "19,152.00" in text
    assert "Menor preço em dinheiro" in text and "kayak" in text.split("Menor preço em dinheiro")[1]
    assert "Equilíbrio" in text and "32.18" in text  # (19152-3000)/502


def test_report_without_any_data_says_so(tmp_path):
    text = build_report(str(tmp_path / "h.csv"), str(tmp_path / "o.csv"))

    assert "sem dados" in text.lower()


def test_report_without_miles_has_no_breakeven(tmp_path):
    others = str(tmp_path / "outras.csv")
    append_check(others, OtherCheck("2026-11-23", "cvc", 18900.0, None, None, ""))

    text = build_report(str(tmp_path / "h.csv"), others)

    assert "Equilíbrio" not in text
    assert "18,900.00" in text

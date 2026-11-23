from verificador.history import HistoryRecord, has_ok_record, last_price, upsert_record


def rec(date, price=19152.0, status="ok"):
    return HistoryRecord(date, price, "KLM", "AMS 7h00 | AMS 5h25", "Light", status)


def test_upsert_creates_file_with_header(tmp_path):
    path = tmp_path / "data" / "history.csv"

    upsert_record(str(path), rec("2026-11-23"))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "date,total_price_brl,airlines,layovers,fare,status"
    assert len(lines) == 2


def test_upsert_same_date_replaces_not_duplicates(tmp_path):
    path = str(tmp_path / "history.csv")

    upsert_record(path, rec("2026-11-23", 19152.0))
    upsert_record(path, rec("2026-11-23", 18000.0))

    lines = open(path, encoding="utf-8").read().splitlines()
    assert len(lines) == 2
    assert "18000.0" in lines[1]


def test_last_price_ignores_error_rows(tmp_path):
    path = str(tmp_path / "history.csv")
    upsert_record(path, rec("2026-11-21", 19500.0))
    upsert_record(path, HistoryRecord("2026-11-22", None, "", "", None, "error"))

    assert last_price(path, "2026-11-23") == 19500.0


def test_last_price_only_before_given_date(tmp_path):
    path = str(tmp_path / "history.csv")
    upsert_record(path, rec("2026-11-22", 19500.0))
    upsert_record(path, rec("2026-11-23", 18000.0))

    assert last_price(path, "2026-11-23") == 19500.0


def test_last_price_none_on_first_run(tmp_path):
    assert last_price(str(tmp_path / "missing.csv"), "2026-11-23") is None


def test_has_ok_record(tmp_path):
    path = str(tmp_path / "history.csv")
    assert has_ok_record(path, "2026-11-23") is False
    upsert_record(path, rec("2026-11-23"))
    upsert_record(path, HistoryRecord("2026-11-22", None, "", "", None, "error"))

    assert has_ok_record(path, "2026-11-23") is True
    assert has_ok_record(path, "2026-11-22") is False
    assert has_ok_record(path, "2026-11-24") is False


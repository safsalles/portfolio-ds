from verificador.other_sources import OtherCheck, append_check, latest_by_source, load_checks


def chk(date, source, price=19152.0, miles=None, taxes=None, note=""):
    return OtherCheck(date, source, price, miles, taxes, note)


def test_append_creates_file_with_header_and_roundtrips(tmp_path):
    path = str(tmp_path / "data" / "outras_fontes.csv")

    append_check(path, chk("2026-11-23", "kayak", 19152, note="KLM Light"))
    append_check(path, chk("2026-11-23", "flying blue", None, 502000, 3000.0))

    lines = open(path, encoding="utf-8").read().splitlines()
    assert lines[0] == "date,source,price_brl,miles,taxes_brl,note"
    loaded = load_checks(path)
    assert len(loaded) == 2
    assert loaded[0].price_brl == 19152.0 and loaded[0].note == "KLM Light"
    assert loaded[1].price_brl is None and loaded[1].miles == 502000 and loaded[1].taxes_brl == 3000.0


def test_load_missing_file_is_empty(tmp_path):
    assert load_checks(str(tmp_path / "nao_existe.csv")) == []


def test_latest_by_source_keeps_newest_per_source():
    checks = [
        chk("2026-11-20", "kayak", 19500),
        chk("2026-11-23", "kayak", 19152),
        chk("2026-11-21", "cvc", 18900),
    ]

    latest = latest_by_source(checks)

    assert latest["kayak"].price_brl == 19152
    assert latest["cvc"].price_brl == 18900
    assert set(latest) == {"kayak", "cvc"}


def test_note_with_comma_survives_roundtrip(tmp_path):
    path = str(tmp_path / "o.csv")

    append_check(path, chk("2026-11-23", "cvc", 18900, note="ida KLM, volta AF"))

    assert load_checks(path)[0].note == "ida KLM, volta AF"

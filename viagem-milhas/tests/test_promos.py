from verificador.promos import (
    extract_milheiro,
    fetch_feed,
    find_promos,
    load_seen,
    save_seen,
)

LIMITS = {"flying blue": 35.0, "tap": 35.0, "livelo": 35.0, "smiles": 12.0}
KEYWORDS = ["flying blue", "smiles", "livelo", "tap", "milheiro", "bônus"]


def entry(title, summary="", link="https://exemplo.test/x"):
    return {"title": title, "summary": summary, "link": link}


def test_extract_milheiro_variants():
    assert extract_milheiro("Compre com milheiro a R$ 29,50 hoje") == 29.5
    assert extract_milheiro("Saindo por R$ 30,10 o milheiro") == 30.1


def test_extract_ignores_other_prices():
    text = "Passagem por R$ 5.192 em executiva. Milheiro a R$ 68 na Livelo."
    assert extract_milheiro(text) == 68.0


def test_extract_none_when_no_milheiro_word():
    assert extract_milheiro("Passagens a partir de R$ 5.192") is None


def test_find_promos_flying_blue_under_35_alerts():
    promos = find_promos(
        [entry("Flying Blue: milheiro a R$ 29", link="https://exemplo.test/a")],
        KEYWORDS, LIMITS, set(),
    )

    assert len(promos) == 1
    assert promos[0].program == "flying blue"
    assert promos[0].milheiro_brl == 29.0
    assert promos[0].link == "https://exemplo.test/a"


def test_find_promos_smiles_needs_under_12():
    assert find_promos([entry("Smiles com milheiro a R$ 17,20")], KEYWORDS, LIMITS, set()) == []
    assert len(find_promos([entry("Smiles com milheiro a R$ 10,90")], KEYWORDS, LIMITS, set())) == 1


def test_find_promos_skips_seen_links():
    e = entry("Flying Blue: milheiro a R$ 29", link="https://exemplo.test/a")

    assert find_promos([e], KEYWORDS, LIMITS, {"https://exemplo.test/a"}) == []


def test_find_promos_without_confident_price_is_silent():
    assert find_promos([entry("Flying Blue tem bônus de 30% hoje")], KEYWORDS, LIMITS, set()) == []


def test_find_promos_two_programs_uses_strictest_limit():
    both_high = entry("Livelo para Smiles com milheiro a R$ 20")
    both_low = entry("Livelo para Smiles com milheiro a R$ 10", link="https://exemplo.test/b")

    assert find_promos([both_high], KEYWORDS, LIMITS, set()) == []
    assert len(find_promos([both_low], KEYWORDS, LIMITS, set())) == 1


def test_find_promos_does_not_match_tap_inside_other_words():
    assert find_promos([entry("Startap lança milheiro a R$ 5")], KEYWORDS, LIMITS, set()) == []


def test_seen_roundtrip_and_missing_file(tmp_path):
    path = str(tmp_path / "data" / "seen.json")

    assert load_seen(path) == set()
    save_seen(path, {"https://exemplo.test/a"})
    assert load_seen(path) == {"https://exemplo.test/a"}


def test_fetch_feed_reads_fixture():
    entries = fetch_feed("tests/fixtures/feed_sample.xml")

    assert len(entries) == 2
    assert entries[0]["link"] == "https://exemplo.test/promo-flying-blue"
    assert "milheiro" in entries[0]["title"].lower()

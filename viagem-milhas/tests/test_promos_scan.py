from verificador.promos import find_promos, scan_promos
from verificador.ui_helpers import promo_verdict

ENTRIES = [
    {"title": "Smiles: compre milhas com milheiro a R$ 14,00", "summary": "", "link": "a"},
    {"title": "Livelo: compra de pontos, milheiro a R$ 40,00", "summary": "", "link": "b"},
    {"title": "Receita de bolo", "summary": "sem milhas", "link": "c"},
]
LIMITS = {"smiles": 16.0, "livelo": 30.0}
KEYWORDS = ["compre", "compra"]


def test_scan_lists_every_promo_even_above_the_limit():
    found = scan_promos(ENTRIES, KEYWORDS, LIMITS)

    assert [(p.program, p.milheiro_brl) for p in found] == [("smiles", 14.0), ("livelo", 40.0)]


def test_find_promos_still_keeps_only_cheap_unseen_ones():
    assert [p.link for p in find_promos(ENTRIES, KEYWORDS, LIMITS, set())] == ["a"]
    assert find_promos(ENTRIES, KEYWORDS, LIMITS, {"a"}) == []


def test_verdict_uses_the_breakeven_of_the_trip_when_known():
    assert promo_verdict(14.0, 16.0, 20.0) == "Compensa nesta viagem"
    assert promo_verdict(25.0, 30.0, 20.0) == "Não compensa nesta viagem"


def test_verdict_falls_back_to_the_configured_limit():
    assert promo_verdict(14.0, 16.0, None) == "Abaixo do seu limite"
    assert promo_verdict(40.0, 30.0, None) == "Acima do seu limite"

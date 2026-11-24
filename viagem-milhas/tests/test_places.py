from verificador.places import describe_codes, looks_like_codes, search_places


def first(query):
    results = search_places(query)
    assert results, f"nenhum resultado para {query!r}"
    return results[0]


def test_portuguese_city_name_finds_the_airport():
    place = first("Lisboa")

    assert place.codes == "LIS"
    assert "Lisboa" in place.label and "Portugal" in place.label


def test_search_ignores_accents_and_case():
    assert first("sao paulo").codes == "GRU,CGH,VCP"
    assert first("SÃO PAULO").codes == "GRU,CGH,VCP"
    assert first("brasília").codes == first("BRASILIA").codes


def test_english_and_portuguese_names_both_work():
    assert first("Budapeste").codes == "BUD"
    assert first("Budapest").codes == "BUD"
    assert first("Lisbon").codes == "LIS"


def test_city_with_several_airports_lists_them_all():
    place = first("Londres")

    assert place.kind == "cidade"
    assert place.codes.split(",")[0] == "LHR" and "LGW" in place.codes.split(",")
    assert "Reino Unido" in place.label


def test_new_york_uses_the_whole_metro_area():
    assert first("Nova York").codes == "JFK,EWR,LGA"
    assert first("new york").codes == "JFK,EWR,LGA"


def test_rio_and_istanbul():
    assert first("Rio de Janeiro").codes == "GIG,SDU"
    assert first("Istambul").codes == "IST,SAW"


def test_airport_name_and_iata_code_work():
    assert any(p.codes == "AMS" for p in search_places("Schiphol"))
    place = first("GRU")
    assert place.codes == "GRU" and place.kind == "aeroporto"


def test_comma_separated_codes_are_accepted_as_they_are():
    assert first("lhr, lgw").codes == "LHR,LGW"


def test_unknown_text_returns_nothing():
    assert search_places("zzzzxq") == []
    assert search_places("") == []
    assert search_places("   ") == []


def test_limit_is_respected():
    assert len(search_places("san", limit=3)) <= 3


def test_looks_like_codes():
    assert looks_like_codes("GRU") and looks_like_codes("gru") and looks_like_codes("LHR,LGW") and looks_like_codes("LHR, LGW")
    assert not looks_like_codes("Lisboa") and not looks_like_codes("XX1") and not looks_like_codes("")


def test_describe_codes_is_readable():
    assert "Rio de Janeiro" in describe_codes("GIG") and "GIG" in describe_codes("GIG")
    text = describe_codes("LHR,LGW")
    assert "Londres" in text and "LHR" in text and "LGW" in text
    assert describe_codes("QQQ") == "QQQ"  # codigo desconhecido volta como veio


def test_main_cities_win_over_namesakes():
    assert first("Paris").codes == "CDG,ORY"  # e nao o Paris dos Estados Unidos
    assert first("Roma").codes == "FCO,CIA"
    assert first("São Petersburgo").country == "Rússia"


def test_cities_outside_the_curated_list_keep_only_the_main_airport():
    assert first("Madri").codes == "MAD"  # sem o aeroporto militar de Torrejon
    assert first("Miami").codes == "MIA"
    assert first("Orlando").codes == "MCO,SFB"


def test_buenos_aires_is_labelled_by_its_name():
    place = first("Buenos Aires")

    assert place.codes == "EZE,AEP" and place.label.startswith("Buenos Aires")


def test_seaplane_bases_and_heliports_are_not_offered():
    assert all("seaplane" not in p.label.lower() for p in search_places("new york", limit=30))

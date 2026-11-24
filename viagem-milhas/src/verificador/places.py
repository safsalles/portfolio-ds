"""Busca de lugares pelo nome (cidade ou aeroporto), para ninguem precisar saber o codigo IATA.

Usa a base offline do pacote `airportsdata` (cerca de 8 mil aeroportos) e `babel` para os nomes dos paises
em portugues. Cidades com mais de um aeroporto (Londres, Nova York, Sao Paulo...) viram um unico lugar com
todos os codigos separados por virgula, que e' o formato que o Google Voos aceita.
"""
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

import airportsdata
from babel import Locale

_CODES = re.compile(r"^[A-Za-z]{3}(\s*,\s*[A-Za-z]{3})*$")
_SMALL_WORDS = {"De", "Do", "Da", "Dos", "Das", "Del", "Di", "Du", "Von", "Am", "Of", "La", "Le"}

# (nome em portugues, nome da cidade na base, em ingles). So o que difere entre os idiomas.
_PT_CITIES = [
    ("Lisboa", "lisbon"), ("Londres", "london"), ("Nova York", "new york"), ("Roma", "rome"), ("Milão", "milan"),
    ("Veneza", "venice"), ("Florença", "florence"), ("Turim", "turin"), ("Nápoles", "naples"), ("Gênova", "genoa"),
    ("Bolonha", "bologna"), ("Genebra", "geneva"), ("Zurique", "zurich"), ("Viena", "vienna"), ("Praga", "prague"),
    ("Varsóvia", "warsaw"), ("Cracóvia", "krakow"), ("Bucareste", "bucharest"), ("Budapeste", "budapest"),
    ("Berlim", "berlin"), ("Munique", "munich"), ("Colônia", "cologne"), ("Hamburgo", "hamburg"),
    ("Estugarda", "stuttgart"), ("Nuremberga", "nuremberg"), ("Salzburgo", "salzburg"), ("Bruxelas", "brussels"),
    ("Amsterdã", "amsterdam"), ("Copenhague", "copenhagen"), ("Estocolmo", "stockholm"),
    ("Gotemburgo", "gothenburg"), ("Helsinque", "helsinki"), ("Atenas", "athens"), ("Tessalônica", "thessaloniki"),
    ("Moscou", "moscow"), ("São Petersburgo", "st petersburg"), ("Belgrado", "belgrade"),
    ("Istambul", "istanbul"), ("Ancara", "ankara"), ("Edimburgo", "edinburgh"), ("Sevilha", "sevilla"),
    ("Saragoça", "zaragoza"), ("Marselha", "marseille"), ("Bordéus", "bordeaux"), ("Estrasburgo", "strasbourg"),
    ("Madri", "madrid"), ("Palma de Maiorca", "palma de mallorca"), ("Marrakech", "marrakech"),
    ("Cidade do Cabo", "cape town"), ("Joanesburgo", "johannesburg"), ("Tóquio", "tokyo"), ("Pequim", "beijing"),
    ("Xangai", "shanghai"), ("Bangkok", "bangkok"), ("Singapura", "singapore"), ("Seul", "seoul"),
    ("Bombaim", "mumbai"), ("Nova Délhi", "new delhi"), ("Cidade do México", "mexico city"),
    ("Montevidéu", "montevideo"), ("Assunção", "asuncion"), ("Bogotá", "bogota"), ("Cairo", "cairo"),
    ("Bruxelas", "brussels"), ("Dublin", "dublin"), ("Oslo", "oslo"), ("Reykjavik", "reykjavik"), ("Kiev", "kyiv"),
]
# grafias alternativas em portugues -> nome em ingles
_PT_EXTRA = {"nova iorque": "new york", "banguecoque": "bangkok", "bombay": "mumbai"}

# Cidades com varios aeroportos: o primeiro e' o principal.
_METRO = {
    ("london", "GB"): ["LHR", "LGW", "STN", "LTN", "LCY"],
    ("paris", "FR"): ["CDG", "ORY"],
    ("new york", "US"): ["JFK", "EWR", "LGA"],
    ("sao paulo", "BR"): ["GRU", "CGH", "VCP"],
    ("rio de janeiro", "BR"): ["GIG", "SDU"],
    ("rome", "IT"): ["FCO", "CIA"],
    ("milan", "IT"): ["MXP", "LIN", "BGY"],
    ("moscow", "RU"): ["SVO", "DME", "VKO"],
    ("tokyo", "JP"): ["HND", "NRT"],
    ("osaka", "JP"): ["KIX", "ITM"],
    ("stockholm", "SE"): ["ARN", "BMA"],
    ("buenos aires", "AR"): ["EZE", "AEP"],
    ("istanbul", "TR"): ["IST", "SAW"],
    ("washington", "US"): ["IAD", "DCA", "BWI"],
    ("chicago", "US"): ["ORD", "MDW"],
    ("bangkok", "TH"): ["BKK", "DMK"],
    ("seoul", "KR"): ["ICN", "GMP"],
    ("belo horizonte", "BR"): ["CNF", "PLU"],
    ("brussels", "BE"): ["BRU", "CRL"],
    ("st petersburg", "RU"): ["LED"],
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ,]", " ", text)).strip()


_PT_TO_EN = {_norm(pt): en for pt, en in _PT_CITIES}
_PT_TO_EN.update(_PT_EXTRA)
_EN_TO_PT = {en: pt for pt, en in _PT_CITIES}  # em duplicados, vale o primeiro


@dataclass(frozen=True)
class Place:
    label: str
    codes: str  # "LIS" ou "LHR,LGW,STN" (varios aeroportos da mesma cidade)
    kind: str  # "cidade" | "aeroporto"
    country: str


def looks_like_codes(text: str) -> bool:
    return bool(_CODES.match(text.strip()))


def _fix_case(name: str) -> str:
    words = name.split()
    return " ".join(w.lower() if i and w in _SMALL_WORDS else w for i, w in enumerate(words))


def _city_pt(city_en: str) -> str:
    return _EN_TO_PT.get(_norm(city_en)) or _fix_case(city_en)


_JUNK = ("seaplane", "heliport", "helipad", "water aerodrome")


@lru_cache(maxsize=1)
def _airports() -> dict:
    return {
        code: a
        for code, a in airportsdata.load("IATA").items()
        if code and not any(w in a["name"].lower() for w in _JUNK)
    }


def _is_international(airport: dict) -> bool:
    name = airport["name"].lower()
    return "international" in name or "intl" in name


@lru_cache(maxsize=1)
def _countries() -> dict:
    return Locale("pt_BR").territories


def _country(iso: str) -> str:
    return _countries().get(iso, iso)


def _city_of(airport: dict) -> str:
    return (airport["city"] or "").split(",")[-1].strip()


@lru_cache(maxsize=1)
def _index() -> list[tuple]:
    """Cada item: (Place, city_norm, city_pt_norm, airport_norm, code_lower, n_airports, importance)."""
    airports = _airports()
    groups: dict[tuple, list[str]] = {}
    for code, a in airports.items():
        groups.setdefault((_norm(_city_of(a)), a["country"]), []).append(code)

    entries: list[tuple] = []
    for (city_norm, iso), group in groups.items():
        if not city_norm:
            continue
        group = sorted(group)
        curated = [c for c in _METRO.get((city_norm, iso), []) if c in airports]
        if curated:
            codes, importance = curated, 3
        else:  # fora da lista: so o(s) aeroporto(s) internacional(is), para nao trazer pistas pequenas ou militares
            intl = [c for c in group if _is_international(airports[c])]
            codes, importance = (intl or group[:1])[:3], 2 if intl else 1
        city_pt = _city_pt(_city_of(airports[group[0]]))
        country = _country(iso)
        if len(codes) == 1:
            label = f"{city_pt}, {country} ({codes[0]})"
        else:
            label = f"{city_pt}, {country} — todos os aeroportos ({', '.join(codes)})"
        entries.append((Place(label, ",".join(codes), "cidade", country), city_norm, _norm(city_pt), "", "", len(codes), importance))
        for code in group:
            a = airports[code]
            plabel = f"{a['name']} ({code}) — {city_pt}, {country}"
            entries.append(
                (Place(plabel, code, "aeroporto", country), city_norm, _norm(city_pt), _norm(a["name"]), code.lower(), 1,
                 2 if _is_international(a) else 1)
            )
    return entries


def _score(variants: list[str], city_norm: str, city_pt_norm: str, airport_norm: str, code_lower: str, is_city: bool):
    best = None
    for v in variants:
        if is_city:
            names = (city_norm, city_pt_norm)
            if v in names:
                s = 0
            elif any(n.startswith(v) for n in names):
                s = 1
            elif any(w.startswith(v) for n in names for w in n.split()):
                s = 2
            elif any(v in n for n in names):
                s = 3
            else:
                continue
        else:
            if v == code_lower:
                s = 0
            elif v in airport_norm.split() or (len(v) >= 4 and v in airport_norm):
                s = 4
            else:
                continue
        best = s if best is None else min(best, s)
    return best


def describe_codes(codes: str) -> str:
    """Texto legivel para um ou mais codigos de aeroporto (ex.: 'Londres, Reino Unido — LHR, LGW (2 aeroportos)')."""
    parts = [c.strip().upper() for c in codes.split(",") if c.strip()]
    airports = _airports()
    if not parts or parts[0] not in airports:
        return codes
    first = airports[parts[0]]
    city, country = _city_pt(_city_of(first)), _country(first["country"])
    if len(parts) == 1:
        return f"{first['name']} ({parts[0]}) — {city}, {country}"
    return f"{city}, {country} — {', '.join(parts)} ({len(parts)} aeroportos)"


def search_places(query: str, limit: int = 8) -> list[Place]:
    q = _norm(query)
    if not q:
        return []
    if looks_like_codes(query):
        codes = [c.strip().upper() for c in query.split(",")]
        airports = _airports()
        if all(c in airports for c in codes):
            kind = "aeroporto" if len(codes) == 1 else "cidade"
            return [Place(describe_codes(",".join(codes)), ",".join(codes), kind, _country(airports[codes[0]]["country"]))]
    variants = [q]
    alias = _PT_TO_EN.get(q)
    if alias:
        variants.append(alias)
    ranked = []
    for place, city_norm, city_pt_norm, airport_norm, code_lower, n, importance in _index():
        score = _score(variants, city_norm, city_pt_norm, airport_norm, code_lower, place.kind == "cidade")
        if score is not None:
            ranked.append((score, 0 if place.kind == "cidade" else 1, -importance, -n, place.label, place))
    ranked.sort(key=lambda r: r[:5])
    results, seen = [], set()
    for *_, place in ranked:
        if place.codes in seen:
            continue
        seen.add(place.codes)
        results.append(place)
        if len(results) >= limit:
            break
    return results

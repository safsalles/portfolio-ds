import json
import os
import re
from dataclasses import dataclass

import feedparser

_NUMBER = r"([\d\.]+(?:,\d+)?)"
# "milheiro a R$ 29,50"  |  "R$ 30,10 o milheiro"  (valor colado a palavra milheiro)
_AFTER = re.compile(r"milheiros?[^R\d]{0,20}R\$\s*" + _NUMBER, re.IGNORECASE)
_BEFORE = re.compile(r"R\$\s*" + _NUMBER + r"\s*(?:o|por|cada|/)?\s*milheiros?", re.IGNORECASE)


@dataclass(frozen=True)
class Promo:
    program: str
    title: str
    link: str
    milheiro_brl: float


def _to_float(raw: str) -> float:
    return float(raw.replace(".", "").replace(",", "."))


def extract_milheiro(text: str) -> float | None:
    values = [_to_float(m) for m in _AFTER.findall(text)] + [_to_float(m) for m in _BEFORE.findall(text)]
    return min(values) if values else None


def _programs_in(text: str, programs: list[str]) -> list[str]:
    lowered = text.lower()
    return [p for p in programs if re.search(rf"\b{re.escape(p)}\b", lowered)]


def find_promos(
    entries: list[dict],
    keywords: list[str],
    max_milheiro: dict[str, float],
    seen: set[str],
) -> list[Promo]:
    promos: list[Promo] = []
    programs = list(max_milheiro)
    for e in entries:
        title, summary, link = e.get("title", ""), e.get("summary", ""), e.get("link", "")
        text = f"{title}. {summary}"
        if link in seen or not any(k in text.lower() for k in keywords):
            continue
        milheiro = extract_milheiro(text)
        if milheiro is None:
            continue
        found = _programs_in(title, programs) or _programs_in(summary, programs)
        if not found:
            continue
        strictest = min(found, key=lambda p: max_milheiro[p])
        if milheiro < max_milheiro[strictest]:
            promos.append(Promo(strictest, title, link, milheiro))
    return promos


def fetch_feed(url: str) -> list[dict]:
    parsed = feedparser.parse(url)
    return [
        {"title": e.get("title", ""), "summary": e.get("summary", ""), "link": e.get("link", "")}
        for e in parsed.entries
    ]


def load_seen(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return set(json.load(f))


def save_seen(path: str, seen: set[str]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)

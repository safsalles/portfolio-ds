import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

PAGE = ROOT / "site" / "index.html"
RES = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))


def page_data() -> dict:
    html = PAGE.read_text(encoding="utf-8")
    return json.loads(re.search(r'<script id="dados" type="application/json">(.*?)</script>', html, re.S).group(1))


def test_page_numbers_come_from_results():
    d = page_data()
    f = RES["forecast"]["reajuste_mensal"]
    assert d["previsao"]["erros"]["modelo"] == pytest.approx(f["wape_model"])
    assert d["previsao"]["erros"]["regra"] == pytest.approx(f["wape_baseline"])
    assert d["equipe"]["custo"] == {s["scenario"]: s["agent_hours_scheduled"] for s in RES["staffing"]}
    got = {c["chave"]: c["janela"] for c in RES["investigacao"]["cenarios"]}
    assert {c["chave"]: c["janela"] for c in d["banco"]["cenarios"]} == got


def test_heatmap_and_week_shapes():
    d = page_data()
    assert len(d["chegadas"]["media"]) == 7 and all(len(r) == 24 for r in d["chegadas"]["media"])
    w = d["previsao"]
    assert len(w["real"]) == len(w["modelo"]) == len(w["regra"]) == 168
    assert all(len(v) == 24 for v in d["equipe"]["por_hora"].values())


def test_titles_claims_hold():
    f = RES["forecast"]["reajuste_mensal"]
    assert abs(f["gain_wape_rel"]) < 0.02  # o título diz "empata"
    rows = {c["chave"]: c["janela"]["espera_media_s"] for c in RES["investigacao"]["cenarios"]}
    assert rows["presenca"] < rows["real"] / 2  # o título diz que contar só os presentes subestima
    pausas = [rows[k] for k in ("pausas2", "pausas5", "pausas10")]
    assert min(pausas) < rows["real"] < max(pausas)  # a faixa das pausas contém o real


def test_question_five_is_three_bars():
    html = PAGE.read_text(encoding="utf-8")
    assert "Dá para confiar na conta?" in html and "Can the numbers be trusted?" in html
    assert 'id="b5"' not in html and 'id="b5m"' not in html

def test_sweep_is_monotonic_enough_and_has_default():
    s = page_data()["varredura"]
    sl = [r["service_level"] for r in s["linhas"]]
    assert all(b >= a - 0.02 for a, b in zip(sl, sl[1:]))
    assert s["atual"] in [r["agents"] for r in s["linhas"]]


def test_page_is_self_contained_and_honest():
    html = PAGE.read_text(encoding="utf-8")
    assert not re.search(r'<(script|link|img|iframe)[^>]+(src|href)=["\']https?://', html)
    assert "fictíci" in html and "fictional" in html
    assert "Technion" in html and "NYC 311" in html
    assert "Users" not in html and "@gmail" not in html
    for i in range(1, 6):
        assert f'id="q{i}"' in html


def test_page_is_up_to_date_with_template():
    from gerar_pagina import render

    assert render(page_data()) == PAGE.read_text(encoding="utf-8")


def test_readmes_link_to_published_page():
    url = "https://safsalles.github.io/portfolio-ds/dimensionamento-equipe/site/"
    for name in ("README.md", "README.en.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert url in text and "docs/pagina.jpg" in text
    assert (ROOT / "docs" / "pagina.jpg").stat().st_size > 10_000

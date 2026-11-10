import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fontes import geekhunter  # noqa: E402

LISTA = ('<html><script id="itemList" type="application/ld+json">'
         + json.dumps({"itemListElement": [
             {"@type": "ListItem", "url": "https://www.geekhunter.com/pt/a/jobs/x-1", "name": "X"},
             {"@type": "ListItem", "url": "https://www.geekhunter.com/pt/b/jobs/y-1", "name": "Y"},
         ]}) + '</script></html>')

VAGA = ('<script type="application/ld+json">'
        + json.dumps({
            "@type": "JobPosting", "title": "Analista de Dados (PowerBI)",
            "datePosted": "2026-11-03", "skills": "Power BI, Python",
            "description": "<p>Monte <b>dashboards</b>.</p>",
            "jobLocation": [{"address": {"addressLocality": "Campinas - SP"}}],
            "hiringOrganization": {"name": "Randstad"},
        }) + '</script>')


def test_links_da_lista_na_ordem():
  assert geekhunter.links_da_lista(LISTA) == [
      "https://www.geekhunter.com/pt/a/jobs/x-1", "https://www.geekhunter.com/pt/b/jobs/y-1"]


def test_pagina_sem_lista_nao_quebra():
  assert geekhunter.links_da_lista("") == []
  assert geekhunter.links_da_lista("<html></html>") == []


def test_converter_le_o_jobposting():
  v = geekhunter.converter(VAGA, "https://x/y", "remoto")
  assert v["titulo"] == "Analista de Dados (PowerBI)"
  assert v["empresa"] == "Randstad"
  assert v["modelo"] == "remoto"
  assert v["fonte"] == "GeekHunter"
  assert v["local"] == "Campinas - SP, Brasil"
  assert "dashboards" in v["descricao"] and "Habilidades: Power BI, Python" in v["descricao"]
  assert "<" not in v["descricao"]


def test_converter_sem_jobposting_devolve_none():
  assert geekhunter.converter("<html></html>", "https://x/y", "remoto") is None

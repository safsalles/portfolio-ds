"""Leitura dos cards de cada site, com textos copiados das páginas reais."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fontes import glassdoor, infojobs, vagas_com  # noqa: E402
from util import data_do_card  # noqa: E402


def test_datas_dos_cards():
  agora = datetime(2026, 11, 8, 12, 0)
  assert data_do_card("24h", agora)[0] == 24 * 60
  assert data_do_card("4 dia(s)", agora)[0] == 4 * 1440
  assert data_do_card("Há 4 dias", agora)[0] == 4 * 1440
  assert data_do_card("30d+", agora)[0] == 30 * 1440
  assert data_do_card("Ontem", agora)[0] == 1440
  assert data_do_card("19/10/2026", agora)[1] == "publicada em 19/10/2026"
  assert data_do_card("Publicada em 05/11 Recrutador ativo", agora)[1] == "publicada em 05/11/2026"
  assert data_do_card("6 nov", agora)[1] == "publicada em 06/11/2026"
  # Sem ano e no futuro: é do ano passado.
  assert data_do_card("5 dez", agora)[1] == "publicada em 05/12/2025"
  assert data_do_card("sem data", agora)[1] == "data n/d"


def test_card_do_glassdoor():
  item = {"href": "https://www.glassdoor.com.br/job-listing/x.htm", "titulo": "Analista de Dados SR",
          "linhas": ["Sysmap", "4,0", "Analista de Dados SR", "Trabalho remoto",
                     "Conhecimento avançado em SQL; Power BI ou Tableau",
                     "Habilidades: Estatística, R, SQL", "Ver mais", "4 dia(s)"]}
  v = glassdoor.ler_card(item)
  assert (v["empresa"], v["modelo"], v["local"]) == ("Sysmap", "remoto", "Brasil")
  assert v["minutos"] == 4 * 1440
  assert "Power BI" in v["descricao"] and "Ver mais" not in v["descricao"]


def test_card_do_infojobs():
  item = {"href": "https://www.infojobs.com.br/vaga-de-x__1.aspx", "titulo": "Analista De Dados Pleno",
          "linhas": ["Analista De Dados Pleno", "6 nov", "4,5", "SPAR BRASIL SERVICOS LTDA.",
                     "São Paulo - SP", "A combinar", "Ensino Superior", "Híbrido",
                     "Se você é uma pessoa analítica..."]}
  v = infojobs.ler_card(item)
  assert v["empresa"] == "SPAR BRASIL SERVICOS LTDA."
  assert v["local"] == "São Paulo - SP, Brasil"
  assert v["modelo"] == "hibrido"
  assert v["descricao"].startswith("Se você")


def test_card_do_infojobs_com_selo_e_data_ontem():
  item = {"href": "https://www.infojobs.com.br/vaga-de-y__2.aspx", "titulo": "Analista De Dados E BI",
          "linhas": ["CONTRATAÇÃO URGENTE", "Analista De Dados E BI", "Ontem", "3,8",
                     "Empresa confidencial", "Barueri - SP", "R$ 3.500,00 a R$ 5.000,00",
                     "Home office"]}
  v = infojobs.ler_card(item)
  assert (v["empresa"], v["local"], v["modelo"]) == (
      "Empresa confidencial", "Barueri - SP, Brasil", "remoto")
  assert v["publicada"] == "ontem"


def test_lista_do_vagas_com():
  html = '''<ul><li class="vaga odd "> <h2 class="cargo"> <a class="link-detalhes-vaga"
    data-id-vaga="2841995" title="Analista de Bi (Business Intelligence)" id="v2841995"
    href="/vagas/v2841995/analista-de-bi"> Analista de Bi </a> </h2>
    <span class="emprVaga"> Hospital Sofia Feldman </span>
    <div class="detalhes"> <p>Experiência com Power BI</p> </div>
    <footer> <div class="vaga-local"> <i class="bx bx-map"></i> Belo Horizonte / MG <div class="tooltip-place">
    </div></div> <span class="data-publicacao"><i class="bx bx-time-five"></i>Há 4 dias</span>
    </footer> </li></ul>'''
  [v] = vagas_com.ler_lista(html)
  assert v["titulo"] == "Analista de Bi (Business Intelligence)"
  assert v["empresa"] == "Hospital Sofia Feldman"
  assert v["local"] == "Belo Horizonte / MG, Brasil"
  assert v["link"] == "https://www.vagas.com.br/vagas/v2841995/analista-de-bi"
  assert v["minutos"] == 4 * 1440

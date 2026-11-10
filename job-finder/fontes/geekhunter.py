"""GeekHunter: lista pública de vagas (geekhunter.com/pt/vagas), sem login.

A própria página documenta os parâmetros da busca (SearchAction):
searchTerm, workModality (remote, remote-in-city, hybrid, on-site) e cityName.
A lista traz só os links; o título, a empresa, a data, o local e a descrição
saem do JobPosting (JSON-LD) de cada vaga.
"""

import json
import re
import time
from urllib.parse import quote

from util import baixar, limpar_html, minutos_desde, nova_vaga

BASE = "https://www.geekhunter.com/pt/vagas?"
MAX_POR_BUSCA = 40   # vagas abertas por busca (cada uma é uma página)
PAUSA = 0.5          # segundos entre páginas, para não incomodar o site

_LISTA = re.compile(r'<script id="itemList" type="application/ld\+json">(.*?)</script>', re.S)
_JSON_LD = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S)


def links_da_lista(html):
  """Endereços das vagas de uma página de busca, na ordem em que aparecem."""
  achou = _LISTA.search(html or "")
  if not achou:
    return []
  try:
    itens = json.loads(achou.group(1)).get("itemListElement") or []
  except ValueError:
    return []
  return [i["url"] for i in itens if i.get("url")]


def converter(html, link, modelo):
  """Vaga (formato único) a partir da página da vaga, ou None se não achar o
  JobPosting. modelo: 'remoto', 'hibrido' ou 'presencial' (vem da busca)."""
  for bloco in _JSON_LD.findall(html or ""):
    try:
      dados = json.loads(bloco)
    except ValueError:
      continue
    if dados.get("@type") != "JobPosting":
      continue
    local = ""
    for lugar in dados.get("jobLocation") or []:
      cidade = (lugar.get("address") or {}).get("addressLocality")
      if cidade:
        local = cidade
        break
    minutos, rotulo = minutos_desde(dados.get("datePosted"))
    descricao = limpar_html(dados.get("description"))
    habilidades = dados.get("skills")
    if habilidades:
      descricao = f"{descricao} Habilidades: {habilidades}".strip()
    return nova_vaga(
        dados.get("title"), (dados.get("hiringOrganization") or {}).get("name"),
        link, "GeekHunter",
        local=f"{local}, Brasil" if local else "Brasil",
        modelo=modelo, minutos=minutos, publicada=rotulo,
        descricao=descricao[:8000],
    )
  return None


def _buscar(parametros, modelo, rotulo):
  html = baixar(BASE + parametros)
  links = links_da_lista(html)[:MAX_POR_BUSCA]
  vagas = []
  for link in links:
    time.sleep(PAUSA)
    vaga = converter(baixar(link, silencioso=True), link, modelo)
    if vaga:
      vagas.append(vaga)
  print(f"   GeekHunter: {rotulo} -> {len(vagas)} vagas")
  return vagas


def buscar(termos):
  """Vagas remotas para cada termo."""
  vagas = {}
  for termo in termos:
    for vaga in _buscar(f"searchTerm={quote(termo)}&workModality=remote", "remoto", f"'{termo}'"):
      vagas.setdefault(vaga["link"], vaga)
  return list(vagas.values())


def buscar_cidade(cidade, termos):
  """Vagas presenciais ou híbridas de uma cidade, para cada termo."""
  vagas = {}
  for termo in termos:
    parametros = (f"searchTerm={quote(termo)}&workModality=hybrid,on-site"
                  f"&cityName={quote(cidade)}")
    for vaga in _buscar(parametros, "hibrido", f"{cidade} '{termo}'"):
      vagas.setdefault(vaga["link"], vaga)
  return list(vagas.values())

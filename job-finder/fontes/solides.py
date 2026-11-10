"""Sólides Vagas (vagas.solides.com.br): lista pública, sem login.

A busca é /vagas/<termo>/remoto?page=N (14 vagas por página). A lista traz
título, empresa e data; a descrição sai da página da vaga (/vaga/<id>), que
tem o JobPosting (JSON-LD). A busca do site é larga (casa o termo até na
descrição), então a classificação do bot é quem filtra os cargos.
"""

import json
import re
import time
from urllib.parse import quote

from util import baixar, limpar_html, minutos_desde, nova_vaga

URL_LISTA = "https://vagas.solides.com.br/vagas/{termo}/remoto?page={pagina}"
URL_VAGA = "https://vagas.solides.com.br/vaga/{id}"
MAX_PAGINAS = 4   # 14 vagas por página
PAUSA = 0.5

_JSON_LD = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
_TITULO = re.compile(r'"id":(\d+),"title":"(.*?)","description"')
_EMPRESA = re.compile(r'"companyName":"(.*?)"')
_DATA = re.compile(r'"createdAt":"([^"]*)"')
_TIPO = re.compile(r'"jobType":"([^"]*)"')


def _texto(valor):
  try:
    return json.loads(f'"{valor}"')  # desfaz & e outros escapes
  except ValueError:
    return valor


def vagas_da_lista(html):
  """Vagas de uma página de busca: (id, título, empresa, data, tipo)."""
  corpo = (html or "").replace('\\"', '"')
  achadas = []
  for pedaco in corpo.split('"killerQuestions"')[1:]:
    t = _TITULO.search(pedaco)
    e = _EMPRESA.search(pedaco)
    if not (t and e):
      continue
    d = _DATA.search(pedaco)
    k = _TIPO.search(pedaco)
    achadas.append((t.group(1), _texto(t.group(2)), _texto(e.group(1)),
                    d.group(1) if d else "", k.group(1) if k else ""))
  return achadas


def converter(id_vaga, titulo, empresa, data, tipo):
  minutos, rotulo = minutos_desde(data)
  return nova_vaga(titulo, empresa, URL_VAGA.format(id=id_vaga), "Sólides",
                   local="Brasil", modelo="remoto" if tipo == "remoto" else "",
                   minutos=minutos, publicada=rotulo)


def buscar(termos):
  """Vagas remotas para cada termo (slug do site, ex.: 'dados', 'power-bi')."""
  vagas = {}
  for termo in termos:
    total = 0
    for pagina in range(1, MAX_PAGINAS + 1):
      html = baixar(URL_LISTA.format(termo=quote(termo), pagina=pagina))
      achadas = vagas_da_lista(html)
      for id_vaga, titulo, empresa, data, tipo in achadas:
        vaga = converter(id_vaga, titulo, empresa, data, tipo)
        vagas.setdefault(vaga["link"], vaga)
      total += len(achadas)
      if not achadas:
        break
      time.sleep(PAUSA)
    print(f"   Sólides: '{termo}' -> {total} vagas")
  return list(vagas.values())


def completar_descricao(vaga):
  """Lê a descrição na página da vaga. False se a página não abre ou não tem
  JobPosting (vaga encerrada)."""
  html = baixar(vaga["link"], silencioso=True)
  for bloco in _JSON_LD.findall(html or ""):
    try:
      dados = json.loads(bloco)
    except ValueError:
      continue
    if dados.get("@type") == "JobPosting":
      vaga["descricao"] = limpar_html(dados.get("description"))[:8000]
      return True
  return False

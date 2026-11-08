"""Gupy: busca do portal de vagas (portal.gupy.io), que tem uma API pública."""

import re
from urllib.parse import quote

from util import baixar_json, limpar_html, minutos_desde, nova_vaga

URL = "https://portal.gupy.io/api/job-search/jobs?jobName={termo}&limit=100&offset=0"
URL_CIDADE = "https://portal.gupy.io/api/job-search/jobs?jobName=&city={cidade}&limit=100&offset={offset}"

MODELOS = {"remote": "remoto", "hybrid": "hibrido", "on-site": "presencial"}


def buscar(termos):
  vagas = {}
  for termo in termos:
    dados = baixar_json(URL.format(termo=quote(termo)))
    if not dados:
      continue
    lista = dados.get("data") or []
    print(f"   Gupy: '{termo}' -> {len(lista)} vagas")
    for j in lista:
      vaga = _converter(j)
      if vaga:
        vagas.setdefault(vaga["link"], vaga)
  return list(vagas.values())


def _converter(j):
  link = (j.get("jobUrl") or "").split("?")[0]
  if not link:
    return None
  minutos, rotulo = minutos_desde(j.get("publishedDate"))
  cidade = ", ".join(x for x in (j.get("city"), j.get("state")) if x)
  return nova_vaga(
      j.get("name"), j.get("careerPageName"), link, "Gupy",
      local=f"{cidade}, Brasil" if cidade else "Brasil",
      modelo=MODELOS.get(j.get("workplaceType"), ""),
      minutos=minutos, publicada=rotulo,
      descricao=limpar_html(j.get("description"))[:8000],
      # A página de carreiras da empresa (de onde sai o "sobre"):
      # https://<empresa>.gupy.io/
      url_empresa=(re.match(r"https://[^/]+/", link) or [""])[0],
  )


def buscar_cidade(cidade, max_paginas=6):
  """Todas as vagas de uma cidade, de 100 em 100."""
  vagas = {}
  for pagina in range(max_paginas):
    dados = baixar_json(URL_CIDADE.format(cidade=quote(cidade), offset=pagina * 100))
    lista = (dados or {}).get("data") or []
    for j in lista:
      vaga = _converter(j)
      if vaga:
        vagas.setdefault(vaga["link"], vaga)
    if len(lista) < 100:
      break
  print(f"   Gupy: {cidade} -> {len(vagas)} vagas")
  return list(vagas.values())

"""InfoJobs: vagas brasileiras. O card diz se a vaga é presencial,
híbrida ou remota, então não precisa abrir a página."""

import re
import time
from urllib.parse import quote_plus

from fontes import cards
from util import data_do_card, normalizar, nova_vaga

URL = "https://www.infojobs.com.br/empregos.aspx?palabra={termo}"
URL_CIDADE = "https://www.infojobs.com.br/empregos-em-{slug}.aspx?page={pagina}"
NOME = "InfoJobs"
PAUSA = 3  # segundos entre buscas
PADRAO_LINK = r"infojobs\.com\.br/vaga-de-.*__\d+\.aspx"
MODELOS = {"presencial": "presencial", "hibrido": "hibrido", "remoto": "remoto",
           "home office": "remoto", "teletrabalho": "remoto"}
DATA = re.compile(r"\d{1,2} [a-z]{3}|hoje|ontem|ha \d+ dias?")
DESCARTAR = re.compile(r"^[\d,. ]+$|selo indica|saiba o que|^nova$|^\.$|km de voce", re.I)


def ler_card(item):
  linhas = item["linhas"]
  titulo = item["titulo"].split("\n")[0]
  if not titulo:
    return None
  # O card é: [selo como "CONTRATAÇÃO URGENTE"], título, data, nota da
  # empresa, empresa, cidade... A leitura parte da data.
  i_data = next((i for i, l in enumerate(linhas) if DATA.fullmatch(normalizar(l))), None)
  data = linhas[i_data] if i_data is not None else ""
  minutos, rotulo = data_do_card(data)
  modelo, i_modelo = "", None
  for i, l in enumerate(linhas):
    if normalizar(l) in MODELOS:
      modelo, i_modelo = MODELOS[normalizar(l)], i
      break
  depois = linhas[i_data + 1:] if i_data is not None else linhas
  resto = [l for l in depois if l != titulo and not DESCARTAR.search(normalizar(l))]
  empresa = resto[0] if resto else ""
  local = resto[1] if len(resto) > 1 else ""
  descricao = ""
  if i_modelo is not None and i_modelo + 1 < len(linhas):
    descricao = linhas[i_modelo + 1]
  return nova_vaga(titulo, empresa, item["href"], "InfoJobs",
                   local=f"{local}, Brasil" if local else "Brasil",
                   modelo=modelo, minutos=minutos, publicada=rotulo,
                   descricao=descricao)


def buscar(termos, browser):
  vagas = {}
  page = cards.nova_pagina(browser)
  for termo in termos:
    itens = cards.ler(page, URL.format(termo=quote_plus(termo)), PADRAO_LINK)
    if itens is None:
      print(f"   {NOME}: bloqueou a busca, parando por hoje")
      break
    lidas = [v for v in (ler_card(it) for it in itens) if v]
    for v in lidas:
      vagas.setdefault(v["link"], v)
    print(f"   InfoJobs: '{termo}' -> {len(lidas)} vagas")
    time.sleep(PAUSA)
  page.close()
  return list(vagas.values())


def buscar_cidade(slug, browser, paginas=3):
  """Vagas de uma cidade. slug é como o InfoJobs escreve a cidade na URL,
  por exemplo "macae,-rj"."""
  vagas = {}
  page = cards.nova_pagina(browser)
  for pagina in range(1, paginas + 1):
    itens = cards.ler(page, URL_CIDADE.format(slug=slug, pagina=pagina), PADRAO_LINK)
    if itens is None:
      print(f"   {NOME}: bloqueou a busca, parando por hoje")
      break
    novas = 0
    for v in (ler_card(it) for it in itens):
      if v and v["link"] not in vagas:
        vagas[v["link"]] = v
        novas += 1
    if not novas:  # a página repetiu as vagas: acabou
      break
    time.sleep(PAUSA)
  page.close()
  print(f"   InfoJobs: {slug} -> {len(vagas)} vagas")
  return list(vagas.values())

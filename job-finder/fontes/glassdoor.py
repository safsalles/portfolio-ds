"""Glassdoor: busca de vagas no Brasil com o filtro de trabalho remoto.

O card traz empresa, título, "Trabalho remoto" (ou a cidade), um trecho da
descrição com as habilidades pedidas (usado na afinidade) e a idade da vaga.
"""

import re
import time

from fontes import cards
from util import data_do_card, normalizar, nova_vaga

# O Glassdoor monta a URL com a posição das palavras: "brasil-<termo>-vagas"
# e KO<início>,<fim> marcando onde está o termo.
URL = ("https://www.glassdoor.com.br/Vaga/brasil-{slug}-vagas-"
       "SRCH_IL.0,6_IN36_KO7,{fim}.htm?remoteWorkType=1&fromAge=14")
NOME = "Glassdoor"
PAUSA = 8  # segundos entre buscas
PADRAO_LINK = r"glassdoor\.com\.br/job-listing/"
IDADE = re.compile(r"\d+\s*(h|d\+|dia\(s\))")


def _url(termo):
  slug = re.sub(r"[^a-z0-9]+", "-", normalizar(termo)).strip("-")
  return URL.format(slug=slug, fim=7 + len(slug))


def ler_card(item):
  linhas = item["linhas"]
  titulo = item["titulo"].split("\n")[0]
  if not titulo or titulo not in linhas:
    return None
  i = linhas.index(titulo)
  # Antes do título: empresa e, às vezes, a nota dela ("4,0").
  antes = [l for l in linhas[:i] if not re.fullmatch(r"\d,\d", l)]
  empresa = antes[0] if antes else ""
  local = linhas[i + 1] if i + 1 < len(linhas) else ""
  remoto = "remoto" in normalizar(local)
  idade = next((l for l in reversed(linhas) if IDADE.fullmatch(l)), "")
  minutos, rotulo = data_do_card(idade)
  descricao = " ".join(l for l in linhas[i + 2:]
                       if l not in (idade, "Ver mais", "Candidatura rápida"))
  return nova_vaga(titulo, empresa, item["href"], "Glassdoor",
                   local="Brasil" if remoto else f"{local}, Brasil",
                   modelo="remoto" if remoto else "",
                   minutos=minutos, publicada=rotulo, descricao=descricao)


def buscar(termos, browser):
  vagas = {}
  page = cards.nova_pagina(browser)
  for termo in termos:
    itens = cards.ler(page, _url(termo), PADRAO_LINK)
    if itens is None:
      print(f"   {NOME}: bloqueou a busca, parando por hoje")
      break
    lidas = [v for v in (ler_card(it) for it in itens) if v]
    for v in lidas:
      vagas.setdefault(v["link"], v)
    print(f"   Glassdoor: '{termo}' -> {len(lidas)} vagas")
    time.sleep(PAUSA)
  page.close()
  return list(vagas.values())

"""LinkedIn pela busca pública de vagas (sem login).

Não usa a sua conta, então não tem risco de banimento. Em troca, o LinkedIn
limita quantas buscas seguidas aceita: o bot faz poucas, com pausa entre
elas, e se for bloqueado segue com as outras fontes.
"""

import re
import time
from urllib.parse import urlencode

from util import baixar, limpar_html, minutos_desde, nova_vaga

URL_BUSCA = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
URL_VAGA = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id}"

BRASIL = "106057199"
AMERICA_LATINA = "91000011"
MUNDO = "92000000"
REMOTO = "2"  # filtro f_WT do LinkedIn

PAUSA = 6  # segundos entre pedidos


def _ler_cards(html):
  # O modelo (remoto/híbrido/presencial) fica vazio: a busca pública ignora o
  # filtro de remoto, então ele é lido depois na descrição da vaga.
  vagas = []
  for card in html.split("<li>")[1:]:
    m_link = re.search(r'href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"?]+)', card)
    if not m_link:
      continue
    titulo = re.search(r'base-search-card__title">\s*([^<]+)', card)
    empresa = re.search(r'base-search-card__subtitle">[\s\S]*?>\s*([^<]+)</a>', card)
    local = re.search(r'job-search-card__location">\s*([^<]+)', card)
    data = re.search(r'datetime="([^"]+)"', card)
    url_empresa = re.search(r'(https://[a-z]+\.linkedin\.com/company/[^"?]+)', card)
    minutos, rotulo = minutos_desde(data.group(1) if data else None)
    vagas.append(nova_vaga(
        limpar_html(titulo.group(1)) if titulo else "",
        limpar_html(empresa.group(1)) if empresa else "",
        m_link.group(1), "LinkedIn",
        local=limpar_html(local.group(1)) if local else "",
        minutos=minutos, publicada=rotulo,
        url_empresa=url_empresa.group(1) if url_empresa else "",
    ))
  return vagas


SEMANA = "r604800"
MES = "r2592000"


def buscar(buscas):
  """buscas: lista de (palavras, geoId, só_remoto, período[, páginas]). O
  período é SEMANA ou MES (vagas de futebol são raras, então olham o mês
  todo). Cada página traz 10 vagas; sem o 5º item, só a primeira."""
  vagas = {}
  for busca in buscas:
    palavras, geo, so_remoto, periodo = busca[:4]
    paginas = busca[4] if len(busca) > 4 else 1
    total = 0
    for pagina in range(paginas):
      parametros = {"keywords": palavras, "geoId": geo, "f_TPR": periodo, "start": pagina * 10}
      if so_remoto:
        parametros["f_WT"] = REMOTO
      html = baixar(URL_BUSCA + urlencode(parametros), tentativas=2, pausa=PAUSA)
      time.sleep(PAUSA)
      if html is None:
        print(f"   LinkedIn: '{palavras}' bloqueada ou falhou, pulando")
        break
      encontradas = _ler_cards(html)
      total += len(encontradas)
      for v in encontradas:
        vagas.setdefault(v["link"], v)
      if len(encontradas) < 10:
        break
    print(f"   LinkedIn: '{palavras}' -> {total} vagas")
  return list(vagas.values())


def completar_descricao(vaga):
  """Abre a vaga pra ler a descrição (de onde saem o modelo de trabalho e
  se aceita quem mora no Brasil). Devolve False se a vaga já não aceita
  candidaturas."""
  m = re.search(r"-(\d+)$", vaga["link"].rstrip("/"))
  if not m:
    return True
  html = baixar(URL_VAGA.format(id=m.group(1)), tentativas=2, pausa=PAUSA)
  time.sleep(PAUSA)
  if html is None:
    return True
  if re.search(r"no longer accepting applications|não aceita mais candidaturas", html, re.I):
    return False
  corpo = re.search(r'show-more-less-html__markup[^>]*>([\s\S]*?)</div>', html)
  vaga["descricao"] = limpar_html(corpo.group(1) if corpo else html)
  return True


def buscar_cidade(local, paginas=3, periodo=MES):
  """Todas as vagas de uma cidade (sem palavra-chave). local é o texto que o
  LinkedIn entende, como "Macaé, Rio de Janeiro, Brazil"."""
  vagas = {}
  for pagina in range(paginas):
    parametros = {"location": local, "f_TPR": periodo, "start": pagina * 10}
    html = baixar(URL_BUSCA + urlencode(parametros), tentativas=2, pausa=PAUSA)
    time.sleep(PAUSA)
    if html is None:
      print(f"   LinkedIn: {local} bloqueada ou falhou, pulando")
      break
    encontradas = _ler_cards(html)
    for v in encontradas:
      vagas.setdefault(v["link"], v)
    if len(encontradas) < 10:
      break
  print(f"   LinkedIn: {local} -> {len(vagas)} vagas")
  return list(vagas.values())

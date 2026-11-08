"""Vagas.com: a lista vem em HTML simples (sem navegador), mas não diz se a
vaga é remota. Então o bot abre a página das vagas que podem servir (título
de uma das categorias, recentes) e tira o modelo de trabalho da descrição.

O filtro de home office do próprio site cai numa verificação anti-robô, por
isso não é usado.
"""

import re
import time

from util import baixar, data_do_card, limpar_html, nova_vaga

URL_BUSCA = "https://www.vagas.com.br/vagas-de-{slug}"
URL_CIDADE = "https://www.vagas.com.br/vagas-em-{slug}?ordenar_por=mais_recentes"
URL_BASE = "https://www.vagas.com.br"
PAUSA = 5  # segundos entre pedidos; com 2 o site começou a recusar (HTTP 429)


def _campo(padrao, texto):
  m = re.search(padrao, texto, re.S)
  return limpar_html(m.group(1)) if m else ""


def ler_lista(html):
  vagas = []
  for card in re.split(r'<li class="vaga', html)[1:]:
    href = re.search(r'href="(/vagas/v\d+/[^"]+)"', card)
    if not href:
      continue
    minutos, rotulo = data_do_card(_campo(r'data-publicacao">(.*?)</span>', card))
    vagas.append(nova_vaga(
        _campo(r'link-detalhes-vaga"[^>]*title="([^"]+)"', card),
        _campo(r'emprVaga">(.*?)</span>', card),
        URL_BASE + href.group(1), "Vagas.com",
        local=_campo(r'bx-map"></i>(.*?)<div', card) + ", Brasil",
        minutos=minutos, publicada=rotulo,
        descricao=_campo(r'class="detalhes">(.*?)</div>', card),
    ))
  return vagas


def buscar(termos):
  vagas = {}
  for termo in termos:
    slug = re.sub(r"\s+", "-", termo.strip().lower())
    html = baixar(URL_BUSCA.format(slug=slug))
    time.sleep(PAUSA)
    if html is None:
      print(f"   Vagas.com: '{termo}' bloqueada ou falhou, pulando")
      continue
    lidas = ler_lista(html)
    for v in lidas:
      vagas.setdefault(v["link"], v)
    print(f"   Vagas.com: '{termo}' -> {len(lidas)} vagas")
  return list(vagas.values())


def completar_descricao(vaga):
  """Lê a descrição completa (de onde sai o modelo de trabalho). Devolve
  False se o site recusou o pedido, para o bot parar de abrir páginas."""
  html = baixar(vaga["link"], pausa=PAUSA)
  time.sleep(PAUSA)
  if html is None:
    return False
  texto = limpar_html(re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S))
  m = re.search(r"Descrição(.*?)(?:Vagas semelhantes|Compartilhe esta vaga|$)", texto, re.S)
  vaga["descricao"] = (m.group(1) if m else texto)[:6000]
  return True


def buscar_cidade(slug):
  """Vagas de uma cidade. slug é como o site escreve: "macae-rj"."""
  html = baixar(URL_CIDADE.format(slug=slug), pausa=PAUSA)
  time.sleep(PAUSA)
  if html is None:
    print(f"   Vagas.com: {slug} bloqueada ou falhou, pulando")
    return []
  vagas = ler_lista(html)
  print(f"   Vagas.com: {slug} -> {len(vagas)} vagas")
  return vagas

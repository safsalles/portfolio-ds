"""Sua avaliação das empresas (empresas.txt) e a descrição de uma linha que
aparece embaixo de cada vaga.

A descrição vem do empresas.txt. Se a empresa não estiver lá, o bot procura
na Wikipédia (português, depois inglês) e guarda o resultado num cache, pra
não procurar de novo a cada rodada.
"""

import json
import os
import re
import time
from datetime import datetime
from urllib.parse import quote

from util import baixar, baixar_json, limpar_html, normalizar

ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "empresas.txt")
CACHE = os.path.expanduser(r"~\Desktop\aux portfolio\job finder\descricoes_empresas.json")
DIAS_PARA_TENTAR_DE_NOVO = 30  # quando a Wikipédia não achou nada

QUERO_MUITO, QUERO, OK, MEH, EVITAR = "quero muito", "quero", "ok", "meh", "evitar"
NOTAS = [QUERO_MUITO, QUERO, OK, MEH, EVITAR]

URL_WIKI = "https://{lingua}.wikipedia.org/api/rest_v1/page/summary/{titulo}"
# Só aceita o resumo da Wikipédia se parecer falar de uma empresa: evita
# trazer o verbete errado quando o nome é ambíguo ("Constructor", "Atlântico").
PADRAO_EMPRESA = re.compile(
    r"company|corporation|firm|business|bank|retailer|provider|developer|"
    r"manufacturer|conglomerate|startup|subsidiary|multinational|organi[sz]ation|"
    r"empresa|companhia|banco|varejista|multinacional|fabricante|fintech|"
    r"grupo|holding|cooperativa|operadora|instituicao|consultoria")


def carregar(caminho=ARQUIVO):
  """Devolve {nome normalizado: {"nome", "nota", "descricao"}}."""
  avaliacoes = {}
  try:
    with open(caminho, "r", encoding="utf-8") as f:
      for linha in f:
        linha = linha.strip()
        if not linha or linha.startswith("#"):
          continue
        partes = [p.strip() for p in linha.split("|")]
        nota = normalizar(partes[1]) if len(partes) > 1 else OK
        if nota not in NOTAS:
          print(f"   empresas.txt: nota desconhecida '{partes[1]}' em '{partes[0]}', usando ok")
          nota = OK
        avaliacoes[normalizar(partes[0])] = {
            "nome": partes[0], "nota": nota,
            "descricao": partes[2] if len(partes) > 2 else "",
        }
  except FileNotFoundError:
    print(f"Arquivo de avaliação de empresas não encontrado: {caminho}")
  return avaliacoes


def avaliacao(empresa, avaliacoes):
  """Acha a empresa da vaga na sua lista (nome inteiro, sem acento). Se
  mais de uma casar, fica a de nome mais longo ("Grupo Real" > "Real")."""
  nome = normalizar(empresa)
  if not nome:
    return None
  achadas = [chave for chave in avaliacoes
             if re.search(r"(?<![a-z0-9])" + re.escape(chave) + r"(?![a-z0-9])", nome)]
  return avaliacoes[max(achadas, key=len)] if achadas else None


# --- DESCRIÇÃO PELA WIKIPÉDIA (com cache) ---

def _carregar_cache():
  try:
    with open(CACHE, "r", encoding="utf-8") as f:
      return json.load(f)
  except (FileNotFoundError, json.JSONDecodeError):
    return {}


def _salvar_cache(cache):
  os.makedirs(os.path.dirname(CACHE), exist_ok=True)
  with open(CACHE, "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False, indent=1)


def _da_wikipedia(empresa):
  titulo = quote(empresa.strip().replace(" ", "_"))
  for lingua in ("pt", "en"):
    dados = baixar_json(URL_WIKI.format(lingua=lingua, titulo=titulo), silencioso=True)
    time.sleep(1)
    if not dados or dados.get("type") != "standard":
      continue
    curta = (dados.get("description") or "").strip()
    resumo = (dados.get("extract") or "").strip()
    if not PADRAO_EMPRESA.search(normalizar(curta + " " + resumo[:300])):
      continue
    # A descrição curta ("British sports data company") cabe numa linha; se
    # não houver, usa a primeira frase do resumo.
    texto = curta if len(curta) > 15 else resumo.split(". ")[0]
    if texto:
      return f"{texto[:1].upper()}{texto[1:]} (Wikipédia)"
  return ""


# --- DESCRIÇÃO PELA GUPY E PELO LINKEDIN ---

PAUSA_LINKEDIN = 4
_linkedin_bloqueado = False  # se o LinkedIn recusar, para de pedir nesta rodada


def primeira_frase(texto, minimo=40, maximo=200):
  """A primeira frase com conteúdo ("O que te encanta? ❤️" não conta)."""
  frases = re.split(r"(?<=[.!?])\s+", (texto or "").strip())
  frase = next((f for f in frases if len(f) >= minimo), frases[0] if frases else "")
  frase = re.sub(r"^[^\w\"(]+", "", frase)  # emoji ou símbolo no começo
  return frase if len(frase) <= maximo else frase[:maximo].rsplit(" ", 1)[0] + "…"


def ler_sobre_gupy(html):
  """O "sobre" da página de carreiras da Gupy vem num JSON dentro da página."""
  m = re.search(r'"about":"((?:[^"\\]|\\.)*)"', html or "")
  if not m:
    return ""
  try:
    return primeira_frase(limpar_html(json.loads(f'"{m.group(1)}"')))
  except ValueError:
    return ""


def ler_pagina_linkedin(html):
  """Da página pública da empresa no LinkedIn: (descrição, porte).
  A descrição está no <meta description>: "Nome | N seguidores | slogan | sobre"."""
  m = re.search(r'<meta name="description" content="([^"]*)"', html or "")
  texto = ""
  if m:
    partes = [p.strip() for p in limpar_html(m.group(1)).split(" | ")[1:]
              if "seguidores" not in p and "followers" not in p]
    sobre = primeira_frase(partes[-1]) if partes else ""
    texto = sobre if len(sobre) >= 40 or len(partes) < 2 else partes[0]
  m = re.search(r"(?:Tamanho da empresa|Company size)\s*([\d.,]+(?:-[\d.,]+)?\+?\s*(?:funcion\w+|employees))",
                limpar_html(html or ""))
  return texto, (m.group(1) if m else "")


def _da_pagina(url):
  """(texto, porte) da página da empresa na Gupy ou no LinkedIn."""
  global _linkedin_bloqueado
  if "gupy.io" in url:
    return ler_sobre_gupy(baixar(url, silencioso=True)), ""
  if "linkedin.com/company/" in url and not _linkedin_bloqueado:
    html = baixar(url, pausa=PAUSA_LINKEDIN, silencioso=True)
    time.sleep(PAUSA_LINKEDIN)
    if html is None:
      _linkedin_bloqueado = True
      print("   LinkedIn recusou a página de empresa; o resto fica para a próxima rodada")
      return "", ""
    return ler_pagina_linkedin(html)
  return "", ""


def completar_descricoes(vagas, avaliacoes):
  """Põe em cada vaga a nota, a descrição e o porte da empresa.

  A descrição vem do empresas.txt; se a empresa não estiver lá, da página
  dela na Gupy ou no LinkedIn e, por último, da Wikipédia. O porte
  (funcionários) vem do LinkedIn. Tudo fica no cache: cada página é lida
  uma vez só.
  """
  cache = _carregar_cache()
  hoje = datetime.now()
  mudou = False
  for vaga in vagas:
    aval = avaliacao(vaga["empresa"], avaliacoes)
    vaga["nota"] = aval["nota"] if aval else None
    chave = normalizar(vaga["empresa"])
    if not chave:
      vaga["sobre_empresa"] = ""
      continue
    info = cache.get(chave) or {"texto": "", "porte": "", "urls": [], "data": hoje.date().isoformat()}
    info.setdefault("porte", "")
    info.setdefault("urls", [])
    url = vaga.get("url_empresa", "")
    # Página nova da empresa e ainda falta algo (descrição ou porte): lê.
    falta = not info["texto"] or not info["porte"]
    if url and url not in info["urls"] and falta and not (
        "linkedin" in url and _linkedin_bloqueado):
      texto, porte = _da_pagina(url)
      if texto or porte or "gupy" in url:
        info["urls"].append(url)
      info["texto"] = info["texto"] or texto
      info["porte"] = info["porte"] or porte
      cache[chave] = info
      mudou = True
    # Sem descrição: Wikipédia, na primeira vez ou a cada 30 dias.
    velha = (hoje - datetime.fromisoformat(info["data"])).days > DIAS_PARA_TENTAR_DE_NOVO
    if not aval and not info["texto"] and (chave not in cache or velha):
      info["texto"] = _da_wikipedia(vaga["empresa"])
      info["data"] = hoje.date().isoformat()
      cache[chave] = info
      mudou = True

    sobre = aval["descricao"] if aval and aval["descricao"] else info["texto"]
    vaga["sobre_empresa"] = " · ".join(x for x in (sobre, info["porte"]) if x)
  if mudou:
    _salvar_cache(cache)


def empresas_para_avaliar(vagas):
  """Empresas das vagas do e-mail que ainda não estão no empresas.txt, já
  no formato de uma linha pronta pra colar lá."""
  vistas = {}
  for v in vagas:
    if v.get("nota") is None and v["empresa"]:
      vistas.setdefault(normalizar(v["empresa"]), v)
  return [f"{v['empresa']} | ok | {v.get('sobre_empresa', '').replace(' (Wikipédia)', '')}".rstrip(" |")
          for v in sorted(vistas.values(), key=lambda v: normalizar(v["empresa"]))]

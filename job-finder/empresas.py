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

from util import baixar_json, normalizar

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


def completar_descricoes(vagas, avaliacoes):
  """Põe em cada vaga a nota e a descrição da empresa. Empresas fora do
  empresas.txt são procuradas na Wikipédia (uma vez; fica no cache)."""
  cache = _carregar_cache()
  hoje = datetime.now()
  mudou = False
  for vaga in vagas:
    aval = avaliacao(vaga["empresa"], avaliacoes)
    if aval:
      vaga["nota"] = aval["nota"]
      vaga["sobre_empresa"] = aval["descricao"]
      continue
    vaga["nota"] = None
    chave = normalizar(vaga["empresa"])
    if not chave:
      vaga["sobre_empresa"] = ""
      continue
    guardada = cache.get(chave)
    velha = guardada and not guardada["texto"] and (
        hoje - datetime.fromisoformat(guardada["data"])).days > DIAS_PARA_TENTAR_DE_NOVO
    if guardada is None or velha:
      guardada = {"texto": _da_wikipedia(vaga["empresa"]), "data": hoje.date().isoformat()}
      cache[chave] = guardada
      mudou = True
    vaga["sobre_empresa"] = guardada["texto"]
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

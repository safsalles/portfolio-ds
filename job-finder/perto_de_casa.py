"""E-mail "Perto de casa": vagas presenciais e híbridas em Campos dos
Goytacazes, São João da Barra e Macaé.

A busca é ampla (todas as vagas das cidades) e o filtro é pelo título,
com as listas do perto_de_casa.txt: sai o que tem termo de [excluir], fica
o que tem algum termo de [areas]. No e-mail, as vagas vão em ordem de
empresa, sem separar por cargo.
"""

import os
import re

import empresas
from classificacao import MAX_DIAS
from util import SEM_TEMPO, normalizar

ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perto_de_casa.txt")

# Cidades e como cada fonte escreve cada uma.
CIDADES = [
    {"nome": "Campos dos Goytacazes", "gupy": "Campos dos Goytacazes",
     "infojobs": "campos-goytacazes,-rj", "vagas_com": "campos-dos-goytacazes-rj",
     "linkedin": "Campos dos Goytacazes, Rio de Janeiro, Brazil"},
    {"nome": "São João da Barra", "gupy": "São João da Barra",
     "infojobs": "sao-joao-da-barra,-rj", "vagas_com": "sao-joao-da-barra-rj",
     "linkedin": "São João da Barra, Rio de Janeiro, Brazil"},
    {"nome": "Macaé", "gupy": "Macaé",
     "infojobs": "macae,-rj", "vagas_com": "macae-rj",
     "linkedin": "Macaé, Rio de Janeiro, Brazil"},
]
# Para reconhecer a cidade no texto de local de cada fonte.
PADRAO_CIDADE = {c["nome"]: re.compile(r"\b" + normalizar(c["nome"]).replace(" ", r"\s+"))
                 for c in CIDADES}
PADRAO_CIDADE["Campos dos Goytacazes"] = re.compile(r"\bcampos\s+(dos\s+)?goytacazes")


def _padrao(termo):
  """Termo com barra invertida é regex; senão, começo de palavra."""
  if "\\" in termo:
    return re.compile(termo)
  return re.compile(r"\b" + re.escape(normalizar(termo)))


def carregar_filtros(caminho=ARQUIVO):
  filtros = {"sempre": [], "excluir": [], "areas": [],
             "exigencias": [], "exigencias_tecnicas": []}
  secao = None
  with open(caminho, "r", encoding="utf-8") as f:
    for linha in f:
      linha = linha.strip()
      if not linha or linha.startswith("#"):
        continue
      m = re.fullmatch(r"\[(\w+)\]", linha)
      if m:
        secao = m.group(1)
        continue
      if secao in filtros:
        filtros[secao].append(_padrao(linha))
  return filtros


def cidade_da_vaga(vaga):
  local = normalizar(vaga["local"])
  for nome, padrao in PADRAO_CIDADE.items():
    if padrao.search(local):
      return nome
  return None


def titulo_serve(titulo, filtros):
  t = normalizar(titulo)
  if any(p.search(t) for p in filtros["sempre"]):
    return True
  if any(p.search(t) for p in filtros["excluir"]):
    return False
  return any(p.search(t) for p in filtros["areas"])


ACEITA_SUPERIOR = re.compile(r"ensino superior|superior completo|superior em|graduacao|bacharel|"
                             r"formacao superior|nivel superior|engenharia de producao")


def exigencia_que_voce_nao_tem(vaga, filtros):
  """Lê a descrição e devolve o trecho que pede algo que você não tem (ou
  None). Sem descrição, não dá para saber: a vaga passa."""
  d = normalizar(vaga.get("descricao", ""))
  if not d:
    return None
  for p in filtros["exigencias"]:
    m = p.search(d)
    if m:
      return m.group(0)
  if not ACEITA_SUPERIOR.search(d):
    for p in filtros["exigencias_tecnicas"]:
      m = p.search(d)
      if m:
        return m.group(0)
  return None


def tirar_por_exigencia(vagas, filtros):
  """Tira as vagas cuja descrição exige algo que você não tem."""
  ficam = []
  for v in vagas:
    motivo = exigencia_que_voce_nao_tem(v, filtros)
    if motivo:
      print(f"   tirada pela descrição ({motivo!r}): {v['titulo'][:50]} | {v['empresa'][:25]}")
    else:
      ficam.append(v)
  return ficam


def filtrar(vagas, filtros, avaliacoes):
  """Fica com as vagas presenciais/híbridas das cidades, recentes, cujo
  título passa nos filtros. Põe em cada uma a cidade e a nota da empresa."""
  aceitas, vistas = [], set()
  cortes = {"fora das cidades": 0, "remota": 0, "antiga": 0, "cargo": 0,
            "empresa confidencial ou a evitar": 0, "repetida": 0}
  for vaga in vagas:
    cidade = cidade_da_vaga(vaga)
    if cidade is None:
      cortes["fora das cidades"] += 1
      continue
    if vaga["modelo"] == "remoto" or re.search(r"remot|home office", normalizar(vaga["titulo"])):
      cortes["remota"] += 1
      continue
    if vaga["minutos"] != SEM_TEMPO and vaga["minutos"] > MAX_DIAS * 1440:
      cortes["antiga"] += 1
      continue
    if not titulo_serve(vaga["titulo"], filtros):
      cortes["cargo"] += 1
      continue
    aval = empresas.avaliacao(vaga["empresa"], avaliacoes)
    vaga["nota"] = aval["nota"] if aval else None
    if vaga["nota"] == empresas.EVITAR or re.search(r"confiden", normalizar(vaga["empresa"])):
      cortes["empresa confidencial ou a evitar"] += 1
      continue
    # A mesma vaga em duas fontes: título + empresa + cidade.
    chave = (normalizar(vaga["titulo"]), normalizar(vaga["empresa"]), cidade)
    if chave in vistas:
      cortes["repetida"] += 1
      continue
    vistas.add(chave)
    vaga["cidade"] = cidade
    aceitas.append(vaga)
  print(f"Perto de casa: {len(aceitas)} vagas aceitas (cortadas: {cortes})")
  return ordenar(aceitas)


def ordenar(vagas):
  """Por empresa (as sem empresa no fim) e, dentro dela, das mais recentes."""
  return sorted(vagas, key=lambda v: (not v["empresa"], normalizar(v["empresa"]), v["minutos"]))

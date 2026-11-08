"""Guarda as vagas já enviadas, para cada vaga chegar no e-mail uma vez só.

O arquivo fica fora do repositório, junto do config_vagas.txt.
"""

import json
import os
from datetime import date, timedelta

from util import normalizar

CAMINHO = os.path.expanduser(r"~\Desktop\aux portfolio\job finder\vagas_vistas.json")
DIAS_PARA_ESQUECER = 120  # depois disso, se a vaga voltar a aparecer, ela é enviada de novo


def chaves(vaga):
  """Duas chaves por vaga: o link e título+empresa. A segunda pega a mesma
  vaga publicada em duas fontes (ex.: Gupy e Remotar)."""
  return [
      vaga["link"].split("?")[0].rstrip("/"),
      f"{normalizar(vaga['titulo'])}|{normalizar(vaga['empresa'])}",
  ]


def carregar(caminho=CAMINHO):
  try:
    with open(caminho, "r", encoding="utf-8") as f:
      return json.load(f)
  except FileNotFoundError:
    return {}
  except ValueError:
    print(f"Arquivo de memória corrompido, começando do zero: {caminho}")
    return {}


def filtrar_novas(vagas, vistas):
  """Tira as vagas já enviadas e as repetidas dentro da própria lista."""
  novas, nesta_rodada = [], set()
  for vaga in vagas:
    ks = chaves(vaga)
    if any(k in vistas or k in nesta_rodada for k in ks):
      continue
    nesta_rodada.update(ks)
    novas.append(vaga)
  return novas


def salvar(vagas_enviadas, vistas, caminho=CAMINHO):
  hoje = date.today().isoformat()
  limite = (date.today() - timedelta(days=DIAS_PARA_ESQUECER)).isoformat()
  vistas = {k: d for k, d in vistas.items() if d >= limite}
  for vaga in vagas_enviadas:
    for k in chaves(vaga):
      vistas[k] = hoje
  os.makedirs(os.path.dirname(caminho), exist_ok=True)
  with open(caminho, "w", encoding="utf-8") as f:
    json.dump(vistas, f, ensure_ascii=False, indent=0)

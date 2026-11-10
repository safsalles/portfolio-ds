"""Vagas coletadas que ainda não foram por e-mail.

Fluxo em duas fases: `--coletar` guarda as vagas aqui (e monta a fila de
candidaturas); o assistente se candidata; `--enviar` lê o arquivo, tira as
vagas em que o Sérgio já se candidatou e só então manda o e-mail.
"""

import json
import os

PASTA = os.path.expanduser(r"~\Desktop\aux portfolio\job finder")


def caminho(nome):
  return os.path.join(PASTA, f"pendentes_{nome}.json")


def salvar(nome, vagas, pasta=None):
  os.makedirs(pasta or PASTA, exist_ok=True)
  with open(os.path.join(pasta, f"pendentes_{nome}.json") if pasta else caminho(nome),
            "w", encoding="utf-8") as f:
    json.dump(vagas, f, ensure_ascii=False, indent=1, default=list)


def carregar(nome, pasta=None):
  arquivo = os.path.join(pasta, f"pendentes_{nome}.json") if pasta else caminho(nome)
  if not os.path.exists(arquivo):
    return None
  with open(arquivo, encoding="utf-8") as f:
    return json.load(f)


def apagar(nome, pasta=None):
  arquivo = os.path.join(pasta, f"pendentes_{nome}.json") if pasta else caminho(nome)
  if os.path.exists(arquivo):
    os.remove(arquivo)

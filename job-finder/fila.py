"""Fila de candidaturas: separa as vagas que o assistente (Claude no Chrome)
pode enviar sozinho das que precisam do Sérgio.

Vai para a fila "voce" (o assistente NÃO envia) quando:
- a empresa tem nota "quero" ou "quero muito" (currículo sob medida);
- a vaga fala em CPF;
- a vaga é de futebol (tem funil próprio).
As demais vão para "auto". Durante o preenchimento o assistente ainda manda a
vaga para "voce" se achar CAPTCHA, teste, conta nova, senha ou pergunta que a
base (perfil.md + gerador-curriculos) não responde.
"""

import json
import os
import re

from classificacao import FUTEBOL
from util import normalizar

CAMINHO = os.path.expanduser(r"~\Desktop\aux portfolio\job finder\fila_candidaturas.json")
NOTAS_DO_SERGIO = ("quero", "quero muito")

_CPF = re.compile(r"\bcpf\b")
_INGLES = re.compile(r"\b(the|and|you|our|we are|experience|team|with)\b")
_ESPANHOL = re.compile(r"\b(nuestro|experiencia|equipo|trabajo|con|para el|los|las)\b")

CURRICULO_POR_CATEGORIA = {"Análise de Dados": "Dados", "Analista de BI": "Dados",
                           "Analista/Assistente Administrativo": "Varejo",
                           "Outras (Engenharia de Produção/Planejamento)": "Engenharia"}


def idioma(vaga):
  """PT, EN ou ES, pelo texto da vaga."""
  texto = normalizar(f"{vaga.get('titulo', '')} {vaga.get('descricao', '')}")[:3000]
  en, es = len(_INGLES.findall(texto)), len(_ESPANHOL.findall(texto))
  pt = len(re.findall(r"\b(de|para|voce|experiencia em|vaga|nossa)\b", texto))
  if en > pt and en >= es:
    return "EN"
  if es > pt and es > en:
    return "ES"
  return "PT"


def curriculo(vaga):
  area = CURRICULO_POR_CATEGORIA.get(vaga.get("categoria"), "Dados")
  return f"Sergio_Salles_{area}_{idioma(vaga)}.pdf"


def grupo(vaga, notas_empresas):
  """('auto' | 'voce', motivo)."""
  nota = (notas_empresas.get(normalizar(vaga.get("empresa", ""))) or {}).get("nota", "")
  if nota in NOTAS_DO_SERGIO:
    return "voce", f"empresa '{nota}': currículo sob medida"
  if _CPF.search(normalizar(vaga.get("descricao", ""))):
    return "voce", "pede CPF"
  if vaga.get("categoria") == FUTEBOL:
    return "voce", "vaga de futebol"
  if vaga.get("modelo") != "remoto":
    return "voce", "modelo de trabalho não confirmado como remoto"
  return "auto", ""


def montar(vagas, estado, codigo):
  """Entradas novas da fila, sem as que já têm resposta ou já estão na fila."""
  notas = estado.get("notas_empresas", {})
  fila = []
  for v in vagas:
    cod = codigo(v)
    if cod in estado.get("vagas", {}):
      continue
    g, motivo = grupo(v, notas)
    fila.append({"codigo": cod, "titulo": v["titulo"], "empresa": v["empresa"],
                 "link": v["link"], "grupo": g, "motivo": motivo,
                 "curriculo": curriculo(v), "status": "pendente"})
  return fila


def salvar(novas, caminho=CAMINHO):
  """Junta às entradas antigas (a mais antiga vence, pra não perder o status)."""
  atual = []
  if os.path.exists(caminho):
    with open(caminho, encoding="utf-8") as f:
      atual = json.load(f)
  vistos = {e["codigo"] for e in atual}
  atual += [e for e in novas if e["codigo"] not in vistos]
  with open(caminho, "w", encoding="utf-8") as f:
    json.dump(atual, f, ensure_ascii=False, indent=1)
  return atual

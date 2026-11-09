"""Respostas ao e-mail: "já me candidatei", "descartar" e "nunca mais essa empresa".

Cada vaga do e-mail tem três links. Clicar abre um e-mail pronto, com
assunto do tipo "Radar: candidatei #1a2b3c4d (Analista de Dados | Acme)";
é só enviar. Na rodada seguinte o bot lê essas respostas pelo IMAP do Gmail
(só as que vieram do seu e-mail e com assunto começando por "Radar:") e:

  candidatei   a vaga sai da lista e vai para a seção "Já me candidatei"
               (fica lá por DIAS_CANDIDATADA dias, com a data);
  descartar    a vaga não volta mais;
  nunca mais   a empresa passa a ser "evitar": nenhuma vaga dela volta;
  nota         (nas "Empresas novas para você avaliar") quero muito, quero,
               ok, meh ou evitar: vale por cima do empresas.txt.

O estado fica em status_vagas.json, fora do repositório.
"""

import email
import hashlib
import imaplib
import json
import os
import re
from datetime import date, timedelta
from email.header import decode_header
from urllib.parse import quote

from util import empresa_base, normalizar

CAMINHO = os.path.expanduser(r"~\Desktop\aux portfolio\job finder\status_vagas.json")
IMAP_SERVER = "imap.gmail.com"
DIAS_CANDIDATADA = 30   # quanto tempo a vaga fica na seção "Já me candidatei"
DIAS_INDICE = 120       # quanto tempo o bot lembra de cada vaga enviada
DIAS_LER = 60           # lê as respostas dos últimos N dias

CANDIDATEI, DESCARTAR, NUNCA_MAIS = "candidatei", "descartar", "nunca mais"
ACOES = (CANDIDATEI, DESCARTAR, NUNCA_MAIS)
NOTA = "nota "  # "nota quero muito", "nota quero", "nota ok", "nota meh", "nota evitar"
ASSUNTO = re.compile(r"radar:\s*(candidatei|descartar|nunca mais|"
                     r"nota (?:quero muito|quero|ok|meh|evitar))\s*#([0-9a-f]{8})")


def _hash(chave):
  return hashlib.sha1(chave.encode("utf-8")).hexdigest()[:8]


def codigo(vaga):
  """8 caracteres, de título + empresa sem sufixos (a mesma vaga em duas
  fontes, "Vetta Tecnologia" e "Vetta", tem o mesmo código)."""
  return _hash(f"{normalizar(vaga['titulo'])}|{empresa_base(vaga['empresa'])}")


def codigo_antigo(vaga):
  """Código de antes, com o nome exato da empresa: as respostas já guardadas
  usam ele."""
  return _hash(f"{normalizar(vaga['titulo'])}|{normalizar(vaga['empresa'])}")


def link_nota(nota, empresa, destinatario):
  """mailto: que dá uma nota à empresa (quero muito, quero, ok, meh, evitar)."""
  cod = _hash(empresa_base(empresa))
  assunto = f"Radar: {NOTA}{nota} #{cod} ({empresa})"
  corpo = "É só enviar este e-mail. O bot lê na próxima rodada."
  return f"mailto:{destinatario}?subject={quote(assunto)}&body={quote(corpo)}"


def link_resposta(acao, vaga, destinatario):
  """mailto: que abre o e-mail de resposta já preenchido."""
  if acao == NUNCA_MAIS:
    sobre = vaga["empresa"] or "empresa não informada"
  else:
    sobre = f"{vaga['titulo']} | {vaga['empresa'] or 'empresa não informada'}"
  assunto = f"Radar: {acao} #{codigo(vaga)} ({sobre})"
  corpo = "É só enviar este e-mail. O bot lê na próxima rodada."
  return f"mailto:{destinatario}?subject={quote(assunto)}&body={quote(corpo)}"


# --- ESTADO ---

def vazio():
  return {"vagas": {}, "empresas_evitar": {}, "notas_empresas": {}, "indice": {}}


def carregar(caminho=CAMINHO):
  try:
    with open(caminho, "r", encoding="utf-8") as f:
      estado = json.load(f)
  except FileNotFoundError:
    return vazio()
  except ValueError:
    print(f"Arquivo de status corrompido, começando do zero: {caminho}")
    return vazio()
  for chave, valor in vazio().items():
    estado.setdefault(chave, valor)
  return estado


def salvar(estado, caminho=CAMINHO):
  os.makedirs(os.path.dirname(caminho), exist_ok=True)
  with open(caminho, "w", encoding="utf-8") as f:
    json.dump(estado, f, ensure_ascii=False, indent=1)


def lembrar(estado, vagas, email_de_origem, hoje=None):
  """Guarda as vagas enviadas no índice, para achar a vaga pelo código."""
  hoje = (hoje or date.today()).isoformat()
  limite = (date.fromisoformat(hoje) - timedelta(days=DIAS_INDICE)).isoformat()
  estado["indice"] = {c: v for c, v in estado["indice"].items() if v["data"] >= limite}
  for v in vagas:
    estado["indice"][codigo(v)] = {
        "titulo": v["titulo"], "empresa": v["empresa"], "link": v["link"],
        "local": v.get("cidade") or v.get("local", ""), "email": email_de_origem, "data": hoje,
    }


def aplicar(estado, acao, cod, sobre="", data=None):
  """Registra uma resposta. `sobre` é o texto entre parênteses do assunto,
  usado se a vaga não estiver no índice."""
  data = data or date.today().isoformat()
  vaga = estado["indice"].get(cod)
  if acao.startswith(NOTA):
    # A resposta mais recente vence: dar nota tira a empresa de "nunca mais".
    empresa = sobre.strip()
    if empresa:
      estado["empresas_evitar"].pop(normalizar(empresa), None)
      estado["notas_empresas"][normalizar(empresa)] = {
          "nome": empresa, "nota": acao[len(NOTA):], "data": data}
    return
  if acao == NUNCA_MAIS:
    empresa = vaga["empresa"] if vaga else sobre.strip()
    if empresa and normalizar(empresa) not in ("", "empresa nao informada"):
      estado["empresas_evitar"][normalizar(empresa)] = empresa
      estado["notas_empresas"].pop(normalizar(empresa), None)
    return
  if not vaga and "|" in sobre:
    titulo, empresa = (p.strip() for p in sobre.split("|", 1))
    vaga = {"titulo": titulo, "empresa": empresa, "link": "", "local": "", "email": "radar"}
  registro = dict(vaga or {}, acao=acao, data=data)
  anterior = estado["vagas"].get(cod)
  if anterior and anterior["acao"] == acao:
    registro["data"] = anterior["data"]  # a mesma resposta lida de novo
  estado["vagas"][cod] = registro


# --- LEITURA DO GMAIL ---

def _texto(cabecalho):
  partes = []
  for pedaco, cod in decode_header(cabecalho or ""):
    partes.append(pedaco.decode(cod or "utf-8", "replace") if isinstance(pedaco, bytes) else pedaco)
  return "".join(partes)


def ler_assunto(assunto):
  """(acao, codigo, sobre) de um assunto "Radar: ...", ou None."""
  assunto = re.sub(r"^(\s*(re|res|fw|fwd|enc)\s*:\s*)+", "", assunto, flags=re.I)
  m = ASSUNTO.search(normalizar(assunto))
  if not m:
    return None
  sobre = re.search(r"\((.*)\)\s*$", assunto)
  return m.group(1), m.group(2), sobre.group(1) if sobre else ""


def ler_respostas(estado, usuario, senha_app, meu_email):
  """Lê no Gmail as respostas mandadas do seu e-mail e atualiza o estado.
  Se o IMAP falhar, avisa e segue: o resto do bot roda igual."""
  if not (usuario and senha_app and meu_email):
    return 0
  desde = (date.today() - timedelta(days=DIAS_LER)).strftime("%d-%b-%Y")
  lidas = 0
  try:
    with imaplib.IMAP4_SSL(IMAP_SERVER) as imap:
      imap.login(usuario, senha_app)
      imap.select("INBOX", readonly=True)
      status, dados = imap.search(None, "FROM", f'"{meu_email}"', "SUBJECT", '"Radar:"',
                                  "SINCE", desde)
      if status != "OK":
        return 0
      for num in dados[0].split():
        status, msg = imap.fetch(num, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
        if status != "OK":
          continue
        cab = email.message_from_bytes(msg[0][1])
        if meu_email.lower() not in _texto(cab["From"]).lower():
          continue
        lido = ler_assunto(_texto(cab["Subject"]))
        if not lido:
          continue
        try:
          data = email.utils.parsedate_to_datetime(cab["Date"]).date().isoformat()
        except (TypeError, ValueError):
          data = None
        aplicar(estado, *lido, data=data)
        lidas += 1
  except (imaplib.IMAP4.error, OSError) as e:
    print(f"Não deu para ler as respostas no Gmail ({e}). Seguindo sem elas.")
    return 0
  print(f"{lidas} resposta(s) lida(s) no Gmail: {len(estado['vagas'])} vagas marcadas,"
        f" {len(estado['empresas_evitar'])} empresas em 'nunca mais'")
  return lidas


# --- USO NO BOT ---

def evitar_empresas(estado, avaliacoes):
  """Aplica por cima do empresas.txt (sem mexer nele) as notas que você deu
  por e-mail e as empresas de "nunca mais", que viram evitar."""
  import empresas
  for chave, dado in estado["notas_empresas"].items():
    if chave in avaliacoes:
      avaliacoes[chave]["nota"] = dado["nota"]
    else:
      avaliacoes[chave] = {"nome": dado["nome"], "nota": dado["nota"], "descricao": ""}
  for chave, nome in estado["empresas_evitar"].items():
    if chave in avaliacoes:
      avaliacoes[chave]["nota"] = empresas.EVITAR
    else:
      avaliacoes[chave] = {"nome": nome, "nota": empresas.EVITAR, "descricao": ""}


def tirar_marcadas(vagas, estado):
  """Tira das listas as vagas descartadas e as que você já se candidatou."""
  ficam = [v for v in vagas
           if codigo(v) not in estado["vagas"] and codigo_antigo(v) not in estado["vagas"]]
  if len(ficam) < len(vagas):
    print(f"   {len(vagas) - len(ficam)} vaga(s) tirada(s): já candidatada ou descartada")
  return ficam


def candidatadas(estado, email_de_origem, hoje=None):
  """Vagas que você se candidatou nos últimos DIAS_CANDIDATADA dias, mais recentes primeiro."""
  limite = ((hoje or date.today()) - timedelta(days=DIAS_CANDIDATADA)).isoformat()
  lista = [v for v in estado["vagas"].values()
           if v["acao"] == CANDIDATEI and v["data"] >= limite
           and v.get("email", "radar") == email_de_origem]
  return sorted(lista, key=lambda v: v["data"], reverse=True)

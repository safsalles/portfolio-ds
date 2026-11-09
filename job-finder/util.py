"""Funções pequenas usadas por todas as fontes: texto, datas e HTTP."""

import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

SEM_TEMPO = 999999999  # vagas sem data vão pro fim da lista


def normalizar(texto):
  """Minúsculo e sem acento, pra comparar 'Híbrido' com 'hibrido'."""
  texto = unicodedata.normalize("NFD", (texto or "").lower())
  return "".join(c for c in texto if unicodedata.category(c) != "Mn")


# Palavras que muitas fontes põem (ou não) no nome da mesma empresa:
# "Vetta Tecnologia" no Gupy, "Vetta" no LinkedIn.
_PALAVRAS_DE_EMPRESA = {
    "ltda", "sa", "s", "a", "me", "epp", "eireli", "inc", "llc", "corp", "co",
    "tecnologia", "tecnologias", "technology", "technologies", "tech",
    "brasil", "brazil", "do", "da", "de", "e", "grupo", "group", "holding",
    "solucoes", "solutions", "servicos", "services", "sistemas", "software",
    "consultoria", "consulting",
}


def empresa_base(nome):
  """Nome da empresa sem sufixos como Ltda, S.A., Tecnologia, Brasil, Grupo,
  só para achar a mesma empresa escrita de dois jeitos."""
  palavras = re.sub(r"[^a-z0-9]+", " ", normalizar(nome)).split()
  uteis = [p for p in palavras if p not in _PALAVRAS_DE_EMPRESA]
  return " ".join(uteis or palavras)


def limpar_html(texto):
  """Tira as tags e junta os espaços de uma descrição em HTML."""
  texto = html.unescape(texto or "")
  texto = re.sub(r"<[^>]+>", " ", texto)
  return re.sub(r"\s+", " ", html.unescape(texto)).strip()


def baixar(url, tentativas=2, pausa=5, silencioso=False):
  """GET simples. Devolve o texto, ou None se a página falhar.
  silencioso: não avisa quando a página não existe (404)."""
  for tentativa in range(tentativas):
    try:
      pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
      with urllib.request.urlopen(pedido, timeout=30) as resposta:
        return resposta.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
      if e.code == 429 and tentativa + 1 < tentativas:
        time.sleep(pausa * 3)  # muitos pedidos seguidos: espera mais
        continue
      if not (silencioso and e.code == 404):
        print(f"   HTTP {e.code} em {url[:90]}")
      return None
    except Exception as e:
      print(f"   Falha em {url[:90]}: {e}")
      if tentativa + 1 < tentativas:
        time.sleep(pausa)
  return None


def baixar_json(url, silencioso=False):
  texto = baixar(url, silencioso=silencioso)
  if texto is None:
    return None
  try:
    return json.loads(texto)
  except ValueError:
    print(f"   Resposta não é JSON: {url[:90]}")
    return None


def minutos_desde(data_iso):
  """'2026-11-06T21:48:24Z' -> (minutos atrás, '06/11/2026')."""
  if not data_iso:
    return SEM_TEMPO, "data n/d"
  try:
    texto = str(data_iso).replace("Z", "+00:00")
    if texto.isdigit():  # Lever manda milissegundos
      data = datetime.fromtimestamp(int(texto) / 1000, tz=timezone.utc)
    elif len(texto) == 10:  # só a data
      data = datetime.fromisoformat(texto).replace(tzinfo=timezone.utc)
    else:
      data = datetime.fromisoformat(texto)
      if data.tzinfo is None:
        data = data.replace(tzinfo=timezone.utc)
  except ValueError:
    return SEM_TEMPO, "data n/d"
  minutos = max(0, int((datetime.now(timezone.utc) - data).total_seconds() // 60))
  return minutos, f"publicada em {data:%d/%m/%Y}"


def nova_vaga(titulo, empresa, link, fonte, local="", modelo="",
              minutos=SEM_TEMPO, publicada="data n/d", descricao="",
              fonte_de_futebol=False, url_empresa=""):
  """Formato único de vaga, igual para todas as fontes.

  modelo: "remoto", "hibrido", "presencial" ou "" (não informado).
  fonte_de_futebol: True quando a fonte só tem empresas de futebol.
  url_empresa: página da empresa na fonte (Gupy, LinkedIn), para ler o
  "sobre" dela.
  """
  return {
      "titulo": (titulo or "").strip(),
      "empresa": (empresa or "").strip(),
      "link": link,
      "fonte": fonte,
      "local": (local or "").strip(),
      "modelo": modelo,
      "minutos": minutos,
      "publicada": publicada,
      "descricao": descricao or "",
      "fonte_de_futebol": fonte_de_futebol,
      "url_empresa": url_empresa,
  }


MESES_CURTOS = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
                "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}


def data_do_card(texto, agora=None):
  """Lê a data como os sites de vaga escrevem no card e devolve
  (minutos atrás, rótulo). Entende: '24h', '4 dia(s)', '30d+', 'Há 4 dias',
  'Hoje', 'Ontem', '19/10/2026', '05/11' e '6 nov'. Datas sem ano são do
  ano corrente, ou do anterior se cairiam no futuro."""
  agora = agora or datetime.now()
  t = normalizar(texto)

  def dias_atras(dias, rotulo):
    return int(dias * 1440), rotulo

  m = re.search(r"\b(\d+)\s*h\b", t)
  if m:
    return int(m.group(1)) * 60, f"{m.group(1)} horas atrás"
  if re.search(r"\bhoje\b", t):
    return dias_atras(0, "hoje")
  if re.search(r"\bontem\b", t):
    return dias_atras(1, "ontem")
  m = re.search(r"\b(\d+)\s*d\+", t)
  if m:
    return dias_atras(int(m.group(1)), f"há mais de {m.group(1)} dias")
  m = re.search(r"\b(\d+)\s*(?:dia\(s\)|dias?\b|d\b)", t)
  if m:
    n = int(m.group(1))
    return dias_atras(n, f"{n} dia{'s' if n != 1 else ''} atrás")

  data = None
  m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b", t)
  if m:
    dia, mes, ano = int(m.group(1)), int(m.group(2)), m.group(3)
  else:
    m = re.search(r"\b(\d{1,2})\s+(" + "|".join(MESES_CURTOS) + r")\b", t)
    dia, mes, ano = (int(m.group(1)), MESES_CURTOS[m.group(2)], None) if m else (0, 0, None)
  if dia:
    try:
      data = datetime(int(ano) if ano else agora.year, mes, dia)
      if not ano and data > agora:
        data = data.replace(year=agora.year - 1)
    except ValueError:
      data = None
  if data is None:
    return SEM_TEMPO, "data n/d"
  minutos = max(0, int((agora - data).total_seconds() // 60))
  return minutos, f"publicada em {data:%d/%m/%Y}"

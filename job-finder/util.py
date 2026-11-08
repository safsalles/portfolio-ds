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
              fonte_de_futebol=False):
  """Formato único de vaga, igual para todas as fontes.

  modelo: "remoto", "hibrido", "presencial" ou "" (não informado).
  fonte_de_futebol: True quando a fonte só tem empresas de futebol.
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
  }

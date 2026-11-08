"""Remotar (remotar.com.br): vagas remotas no Brasil, lidas com o Playwright."""

import re
from datetime import datetime
from urllib.parse import quote_plus

from util import SEM_TEMPO, normalizar, nova_vaga

URL_BUSCA = "https://remotar.com.br/search/jobs?q={termo}"

UNIDADES_MIN = {
    "minuto": 1, "hora": 60, "dia": 1440, "semana": 10080,
    "mes": 43200, "ano": 525600,
}

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}

# Pega o texto do card da vaga (sobe a partir do link até achar o card).
# O card tem: título, empresa, "X atrás", "Via ...", tags.
JS_TEXTO_CARD = """
(a) => {
  const links = (n) => {
    const h = new Set(
      [...n.querySelectorAll('a[href*="/job/"]')].map(x => x.getAttribute('href'))
    );
    if (n.matches && n.matches('a[href*="/job/"]')) h.add(n.getAttribute('href'));
    return h;
  };
  let n = a;
  for (let i = 0; i < 8 && n.parentElement; i++) {
    if (links(n.parentElement).size > 1) break;
    n = n.parentElement;
  }
  const t = n.innerText || "";
  return t.length > 1500 ? "" : t;
}
"""


def extrair_tempo(texto):
  """Acha '5 horas atrás' no card. Devolve (minutos, rótulo)."""
  t = normalizar(texto)
  m = re.search(
      r"(\d+|um|uma)\s*(minuto|hora|dia|semana|mes|meses|ano)s?\s*atras", t
  )
  if not m:
    if re.search(r"agora|instantes", t):
      return 0, "agora mesmo"
    return SEM_TEMPO, "data n/d"
  qtd = 1 if m.group(1) in ("um", "uma") else int(m.group(1))
  unidade = "mes" if m.group(2) == "meses" else m.group(2)
  nomes = {"mes": ("mês", "meses")}
  singular, plural = nomes.get(unidade, (unidade, unidade + "s"))
  return qtd * UNIDADES_MIN[unidade], f"{qtd} {singular if qtd == 1 else plural} atrás"


def extrair_data_atualizacao(texto):
  """Lê 'Última atualização: 28 de Outubro de 2026' da página da vaga."""
  t = normalizar(texto)
  m = re.search(
      r"ultima atualizacao:?\s*(\d{1,2})\s*de\s*([a-z]+)\s*de\s*(\d{4})", t
  )
  if not m or not MESES.get(m.group(2)):
    return None, ""
  try:
    fim_do_dia = datetime(int(m.group(3)), MESES[m.group(2)], int(m.group(1)), 23, 59)
  except ValueError:
    return None, ""
  minutos = max(0, int((datetime.now() - fim_do_dia).total_seconds() // 60))
  return minutos, f"atualizada em {fim_do_dia:%d/%m/%Y}"


def modelo_pelas_tags(texto):
  """'100% Remoto' / 'Vaga híbrida' / 'Presencial' nas tags do card."""
  t = normalizar(texto)
  if "hibrid" in t:
    return "hibrido"
  if "presencial" in t:
    return "presencial"
  if "remoto" in t:
    return "remoto"
  return "remoto"  # o Remotar é um site de vagas remotas


def ler_card(titulo, texto_card):
  """Do texto do card tira empresa, tempo e modelo."""
  linhas = [l.strip() for l in texto_card.split("\n") if l.strip()]
  empresa = ""
  if len(linhas) >= 2 and linhas[0] == titulo:
    empresa = linhas[1]
  minutos, rotulo = extrair_tempo(texto_card)
  local = ""
  m = re.search(r"\n([^\n]+, [A-Z]{2})\s*$", texto_card)  # "São Paulo, SP"
  if m:
    local = m.group(1)
  return empresa, minutos, rotulo, modelo_pelas_tags(texto_card), local


def buscar(palavras_chave, browser):
  """Pesquisa cada termo, rola a lista inteira e coleta os cards."""
  vagas = {}
  page = browser.new_page(viewport={"width": 1280, "height": 1800})
  page.route(
      "**/*",
      lambda rota: (
          rota.abort()
          if rota.request.resource_type in ("image", "media", "font")
          else rota.continue_()
      ),
  )

  for termo in palavras_chave:
    print(f"   Remotar: '{termo}'")
    try:
      page.goto(URL_BUSCA.format(termo=quote_plus(termo)), timeout=45000,
                wait_until="domcontentloaded")
      try:
        page.wait_for_selector('a[href*="/job/"]', timeout=15000)
      except Exception:
        print(f"      nenhuma vaga apareceu para '{termo}'")
        continue

      # Rola a lista e vai coletando a cada passo (o site tira do HTML os
      # cards que já ficaram para trás).
      coletadas = {}

      def coletar():
        novas = 0
        for el in page.query_selector_all('a[href*="/job/"]'):
          try:
            link = el.get_attribute("href")
            if not link:
              continue
            if link.startswith("/"):
              link = f"https://remotar.com.br{link}"
            if link in coletadas:
              continue
            titulo = el.inner_text().strip().split("\n")[0]
            if len(titulo) < 5:
              continue
            coletadas[link] = (titulo, el.evaluate(JS_TEXTO_CARD))
            novas += 1
          except Exception:
            continue
        return novas

      page.mouse.move(640, 500)
      estavel = 0
      for _ in range(200):
        if coletar() == 0:
          estavel += 1
          if estavel >= 6:  # 6 passos seguidos sem vaga nova = fim da lista
            break
        else:
          estavel = 0
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(700)

      for link, (titulo, texto_card) in coletadas.items():
        if link in vagas:
          continue
        empresa, minutos, rotulo, modelo, local = ler_card(titulo, texto_card)
        vagas[link] = nova_vaga(
            titulo, empresa, link, "Remotar", local=local or "Brasil",
            modelo=modelo, minutos=minutos, publicada=rotulo,
        )
      print(f"      {len(coletadas)} vagas na lista")
    except Exception as e:
      print(f"      erro na busca por '{termo}': {e}")

  page.close()
  return list(vagas.values())


def completar_datas(vagas, browser):
  """Vagas do Remotar sem 'X atrás' no card: abre a página e lê a data."""
  pendentes = [v for v in vagas if v["fonte"] == "Remotar" and v["minutos"] == SEM_TEMPO]
  if not pendentes:
    return
  print(f"   Remotar: lendo a data de {len(pendentes)} vaga(s)")
  pagina = browser.new_page()
  for v in pendentes:
    try:
      pagina.goto(v["link"], timeout=45000, wait_until="domcontentloaded")
      pagina.wait_for_timeout(2500)
      texto = pagina.inner_text("body")
      # Só o topo da página (tags), pra não confundir com a descrição.
      t = normalizar(texto)
      i = t.find("ultima atualizacao")
      topo = t[i:i + 450] if i >= 0 else ""
      if "hibrid" in topo:
        v["modelo"] = "hibrido"
      elif "presencial" in topo:
        v["modelo"] = "presencial"
      minutos, rotulo = extrair_data_atualizacao(texto)
      if minutos is not None:
        v["minutos"], v["publicada"] = minutos, rotulo
    except Exception as e:
      print(f"      não consegui ler {v['link']}: {e}")
  pagina.close()

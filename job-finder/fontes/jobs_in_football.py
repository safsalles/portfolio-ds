"""Jobs In Football (jobsinfootball.com): vagas de clubes do mundo todo.

O site bloqueia pedidos que não vêm de um navegador, por isso usa o
Playwright, igual ao Remotar.
"""

import re
from datetime import datetime
from urllib.parse import quote_plus

from util import SEM_TEMPO, limpar_html, nova_vaga

URL_BUSCA = "https://jobsinfootball.com/jobs/?q={termo}&pg={pagina}"

# Lê a lista de resultados: cada vaga tem link /job/<id>/, data, título,
# clube e local.
#   Cada vaga tem mais de um link (logo e título); fica o de texto mais longo.
JS_LISTA = """
() => {
  const porLink = new Map();
  for (const a of document.querySelectorAll('a[href*="/job/"]')) {
    const href = a.href.split('?')[0];
    if (!/\\/job\\/\\d+\\//.test(href)) continue;
    const titulo = a.innerText.trim();
    const atual = porLink.get(href);
    if (atual && atual.titulo.length >= titulo.length) continue;
    let card = a;
    for (let i = 0; i < 6 && card.parentElement; i++) {
      card = card.parentElement;
      if (/\\d{2} \\w{3}, 20\\d\\d/.test(card.innerText)) break;
    }
    porLink.set(href, {href, titulo, texto: card.innerText.slice(0, 600)});
  }
  return [...porLink.values()];
}
"""

# Na página da vaga: clube, local e descrição.
JS_VAGA = """
() => {
  const t = document.body.innerText;
  const i = t.indexOf('JOB DESCRIPTION');
  return {topo: t.slice(Math.max(0, i - 400), i), descricao: t.slice(i, i + 6000)};
}
"""


def _data(texto):
  m = re.search(r"(\d{2}) (\w{3}), (20\d\d)", texto)
  if not m:
    return SEM_TEMPO, "data n/d"
  try:
    data = datetime.strptime(" ".join(m.groups()), "%d %b %Y")
  except ValueError:
    return SEM_TEMPO, "data n/d"
  minutos = max(0, int((datetime.now() - data).total_seconds() // 60))
  return minutos, f"publicada em {data:%d/%m/%Y}"


def buscar(termos, browser, paginas=2):
  candidatas = {}
  page = browser.new_page()
  for termo in termos:
    for pagina in range(1, paginas + 1):
      try:
        page.goto(URL_BUSCA.format(termo=quote_plus(termo), pagina=pagina),
                  timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        itens = page.evaluate(JS_LISTA)
      except Exception as e:
        print(f"   Jobs In Football: erro em '{termo}': {e}")
        break
      for item in itens:
        candidatas.setdefault(item["href"], item)
      if not itens:
        break
    print(f"   Jobs In Football: '{termo}' -> {len(candidatas)} vagas até agora")
  page.close()
  return candidatas


def detalhar(candidatas, browser, filtro_titulo):
  """Abre só as vagas cujo título passa no filtro, pra ler clube, local e
  descrição. Devolve a lista de vagas no formato padrão."""
  vagas = []
  page = browser.new_page()
  for href, item in candidatas.items():
    titulo = item["titulo"].split("\n")[0].strip()
    if not titulo or not filtro_titulo(titulo):
      continue
    try:
      page.goto(href, timeout=45000, wait_until="domcontentloaded")
      page.wait_for_timeout(1500)
      dados = page.evaluate(JS_VAGA)
    except Exception as e:
      print(f"   Jobs In Football: não consegui abrir {href}: {e}")
      continue
    # Topo da página: "Título \n Clube  Local  05 Nov, 2026 \n Full time ..."
    topo = [l.strip() for l in dados["topo"].split("\n") if l.strip()]
    clube, local = "", ""
    for linha in topo:
      if re.search(r"\d{2} \w{3}, 20\d\d", linha):
        sem_data = re.sub(r"\d{2} \w{3}, 20\d\d", "", linha)
        partes = [p.strip() for p in re.split(r"\s{2,}", sem_data) if p.strip()]
        if partes:
          clube = partes[0]
        if len(partes) > 1:
          local = partes[1]
        break
    if not clube:
      # Reserva: na lista, a linha depois do título é "Clube Local".
      linhas = [l.strip() for l in item["texto"].split("\n") if l.strip()]
      if titulo in linhas and linhas.index(titulo) + 1 < len(linhas):
        clube = linhas[linhas.index(titulo) + 1]
    descricao = limpar_html(dados["descricao"])
    m_local = re.search(r"Location:\s*([^\n]{2,60}?)(?:Full Time|Contract|$)", descricao)
    if m_local and not local:
      local = m_local.group(1).strip()
    remoto = bool(re.search(r"work location:\s*remote|fully remote|100% remote",
                            descricao, re.I)) or "remote" in local.lower()
    minutos, rotulo = _data(item["texto"])
    vagas.append(nova_vaga(
        titulo, clube, href, "Jobs In Football", local=local,
        modelo="remoto" if remoto else "", minutos=minutos, publicada=rotulo,
        descricao=descricao, fonte_de_futebol=True,
    ))
  page.close()
  print(f"   Jobs In Football: {len(vagas)} vagas detalhadas")
  return vagas

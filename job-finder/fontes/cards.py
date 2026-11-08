"""Leitura de cards de vaga no navegador, usada pelos sites que só mostram
as vagas renderizadas (Glassdoor, InfoJobs, Catho).

Cada vaga é um link; o card é o maior bloco em volta do link que não
contém outra vaga. Devolve o link, o texto do link e o texto do card,
linha a linha, que cada fonte interpreta do seu jeito.
"""

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

JS_CARDS = r"""
(padrao) => {
  const re = new RegExp(padrao);
  const limpo = (h) => h.split('?')[0].split('#')[0];
  const ehVaga = (a) => re.test(a.href);
  const porLink = new Map();
  for (const a of document.querySelectorAll('a[href]')) {
    if (!ehVaga(a)) continue;
    const href = limpo(a.href);
    let card = a;
    while (card.parentElement) {
      const pai = card.parentElement;
      const outro = [...pai.querySelectorAll('a[href]')]
        .some(x => ehVaga(x) && limpo(x.href) !== href);
      if (outro) break;
      card = pai;
    }
    const titulo = a.innerText.trim();
    const atual = porLink.get(href);
    if (atual && atual.titulo.length >= titulo.length) continue;
    porLink.set(href, {href, titulo, linhas: card.innerText.split('\n')
      .map(l => l.trim()).filter(l => l).slice(0, 30)});
  }
  return [...porLink.values()];
}
"""


def nova_pagina(browser):
  return browser.new_page(locale="pt-BR", user_agent=USER_AGENT)


def ler(page, url, padrao_link, espera=3500):
  """Abre a busca e devolve os cards. Em erro, lista vazia; se o site
  bloqueou (403/429), devolve None, para a fonte parar de insistir."""
  try:
    resposta = page.goto(url, timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(espera)
    if resposta is not None and resposta.status >= 400:
      print(f"      HTTP {resposta.status} em {url[:80]}")
      return None if resposta.status in (403, 429) else []
    return page.evaluate(JS_CARDS, padrao_link)
  except Exception as e:
    print(f"      erro em {url[:80]}: {str(e)[:100]}")
    return []

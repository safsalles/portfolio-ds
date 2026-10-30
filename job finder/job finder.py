import os
import re
import unicodedata
from datetime import datetime
from urllib.parse import quote_plus
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright

# --- LEITURA SEGURA DAS CREDENCIAIS FORA DO GITHUB ---
CONFIG_PATH = os.path.expanduser(
    r"~\Desktop\aux portfolio\job finder\config_vagas.txt"
)

configuracoes = {}
try:
  with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    for linha in f:
      if "=" in linha and not linha.startswith("#"):
        chave, valor = linha.strip().split("=", 1)
        configuracoes[chave.strip()] = valor.strip()
  print("✅ Credenciais carregadas com segurança do arquivo externo!")
except Exception as e:
  print(f"❌ Erro ao ler o arquivo de configuração em {CONFIG_PATH}: {e}")

# Atribuindo às variáveis do bot
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_REMETENTE = configuracoes.get("EMAIL_REMETENTE")
SENHA_APP = configuracoes.get("SENHA_APP")
MEU_EMAIL = configuracoes.get("MEU_EMAIL")

# URL de busca do Remotar (descoberta pelo log do bot).
# Deixe "" para o bot digitar o termo na caixa de busca do site.
URL_BUSCA = "https://remotar.com.br/search/jobs?q={termo}"

# True  = só aceita vagas cujo TÍTULO contenha a palavra-chave.
# False = confia na busca do site (que também olha descrição e tags da vaga).
FILTRAR_POR_TITULO = True

# 🚫 Se o título tiver qualquer um destes termos, a vaga é descartada.
# Não precisa se preocupar com acento nem maiúscula ("hibrido" pega "Híbrido").
EXCLUIR_NO_TITULO = [
    "engenheiro de dados",
    "segurança",
    "arquiteto",
    "hibrido",
    "presencial",
    "infraestrutura",
    "ux/ui",
    "ui/ux",
    "recrutamento",
    "seleção",
    "fiscal",
    "software",
    "mobile",
    "c++",
    "java",
    "engenheiro(a) de dados",
    "engenheira de dados",
]


def normalizar(texto):
  """Minúsculo e sem acento, pra comparar 'Híbrido' com 'hibrido'."""
  texto = unicodedata.normalize("NFD", texto.lower())
  return "".join(c for c in texto if unicodedata.category(c) != "Mn")


EXCLUIR_NORMALIZADO = [normalizar(t) for t in EXCLUIR_NO_TITULO]

# Quanto vale cada unidade, em minutos (pra ordenar por data)
UNIDADES_MIN = {
    "minuto": 1,
    "hora": 60,
    "dia": 1440,
    "semana": 10080,
    "mes": 43200,
    "ano": 525600,
}

# Pega o texto do card da vaga (sobe a partir do link até achar o "X atrás")
JS_TEXTO_CARD = """
(a) => {
  let n = a;
  for (let i = 0; i < 6 && n; i++, n = n.parentElement) {
    const t = n.innerText || "";
    if (/atr[aá]s/i.test(t)) {
      const hrefs = new Set(
        [...n.querySelectorAll('a[href*="/job/"]')].map(x => x.getAttribute('href'))
      );
      if (n.matches('a[href*="/job/"]')) hrefs.add(n.getAttribute('href'));
      return hrefs.size <= 1 ? t : "";
    }
  }
  return "";
}
"""


def extrair_tempo(texto):
  """Acha algo como '5 horas atrás' no texto do card.
  Retorna (minutos, rotulo). Se não achar, (999999999, 'tempo n/d')."""
  t = normalizar(texto or "")
  m = re.search(
      r"(\d+|um|uma)\s*(minuto|hora|dia|semana|mes|meses|ano)s?\s*atras", t
  )
  if not m:
    if re.search(r"agora|instantes", t):
      return 0, "agora mesmo"
    return 999999999, "tempo n/d"

  qtd = 1 if m.group(1) in ("um", "uma") else int(m.group(1))
  unidade = "mes" if m.group(2) == "meses" else m.group(2)
  minutos = qtd * UNIDADES_MIN[unidade]

  nomes = {"mes": ("mês", "meses")}
  singular, plural = nomes.get(unidade, (unidade, unidade + "s"))
  rotulo = f"{qtd} {singular if qtd == 1 else plural} atrás"
  return minutos, rotulo

SEM_TEMPO = 999999999

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}


def extrair_data_atualizacao(texto):
  """Lê 'Última atualização: 28 de Outubro de 2026' da página da vaga.
  Como só vem a data (sem hora), usa 23:59 daquele dia = estimativa mínima
  de quanto tempo faz. Retorna (minutos, rotulo) ou (None, "")."""
  t = normalizar(texto or "")
  m = re.search(
      r"ultima atualizacao:?\s*(\d{1,2})\s*de\s*([a-z]+)\s*de\s*(\d{4})", t
  )
  if not m:
    return None, ""
  dia, mes, ano = int(m.group(1)), MESES.get(m.group(2)), int(m.group(3))
  if not mes:
    return None, ""
  try:
    fim_do_dia = datetime(ano, mes, dia, 23, 59)
  except ValueError:
    return None, ""
  minutos = max(0, int((datetime.now() - fim_do_dia).total_seconds() // 60))
  return minutos, f"atualizada em {dia:02d}/{mes:02d}/{ano}"


# --- SEU PERFIL E PALAVRAS-CHAVE ---
PERFIL_SERGIO = {
    "nome": "Sérgio",
    "email": MEU_EMAIL,
    "mensagem_boas_vindas": (
        "Fala, Sérgio! Encontrei estas oportunidades alinhadas ao seu perfil:"
    ),
    "palavras_chave": [
        "dados",
        "bi",
        "analista",
        "analytics",
        "engenheiro de produção",
        "engenheiro de planejamento",
        "business intelligence",
        "administrative assistant",
        "administrative analyst",
        "data entry",
        "data clerk",
    ],
}


def buscar_e_consolidar_vagas_sergio(palavras_chave):
  """Pesquisa cada termo no Remotar, rola a lista inteira, filtra pelo título,
  consolida e remove duplicadas/estágios."""
  vagas_unicas = {}

  # Palavra inteira, pra "bi" não casar com "bibliotecário", por exemplo
  padroes = [
      re.compile(rf"\b{re.escape(p)}\b", re.IGNORECASE) for p in palavras_chave
  ]

  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
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
      print(f"🔍 Buscando termo '{termo}'")

      try:
        if URL_BUSCA:
          page.goto(
              URL_BUSCA.format(termo=quote_plus(termo)),
              timeout=45000,
              wait_until="domcontentloaded",
          )
        else:
          page.goto(
              "https://remotar.com.br/", timeout=45000, wait_until="domcontentloaded"
          )
          caixa = page.locator(
              'input[type="text"], input[type="search"], input:not([type])'
          ).first
          caixa.fill(termo)
          caixa.press("Enter")
          page.wait_for_timeout(4000)

        print(f"   🌐 URL da busca: {page.url}")

        try:
          page.wait_for_selector('a[href*="/job/"]', timeout=15000)
        except Exception:
          print(f"   ⚠️ Nenhum link de vaga apareceu para '{termo}'")
          page.screenshot(path=f"debug_{termo.replace(' ', '_')}.png")
          continue

        # Rola a lista inteira e vai COLETANDO as vagas a cada passo.
        # (Se o site só mantém ~50 cards no HTML por vez, os de cima somem
        # conforme a gente desce; por isso coleta durante o scroll.)
        coletadas = {}  # link -> (titulo, texto_card)

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
              if not titulo or len(titulo) < 5:
                continue
              texto_card = el.evaluate(JS_TEXTO_CARD)
              coletadas[link] = (titulo, texto_card)
              novas += 1
            except Exception:
              continue
          return novas

        page.mouse.move(640, 500)
        estavel = 0
        for _ in range(200):
          novas = coletar()
          if novas == 0:
            estavel += 1
            if estavel >= 6:  # 6 passos seguidos sem vaga nova = fim da lista
              break
          else:
            estavel = 0
          page.mouse.wheel(0, 1500)
          page.wait_for_timeout(700)

        aceitas = 0
        cortes = {"estágio": 0, "termo proibido": 0, "sem palavra-chave": 0}

        for link, (titulo, texto_card) in coletadas.items():
          # 🚫 Filtro anti-estágio
          if "estag" in titulo.lower():
            cortes["estágio"] += 1
            continue

          # 🚫 Termos proibidos no título
          titulo_norm = normalizar(titulo)
          if any(ruim in titulo_norm for ruim in EXCLUIR_NORMALIZADO):
            cortes["termo proibido"] += 1
            continue

          # 🎯 Filtro opcional por título
          if FILTRAR_POR_TITULO and not any(
              pad.search(titulo) for pad in padroes
          ):
            cortes["sem palavra-chave"] += 1
            continue

          aceitas += 1

          # ⏱️ Tempo no ar (lido do card: "5 horas atrás")
          minutos, rotulo = extrair_tempo(texto_card)

          # 🔄 Deduplicação pelo link
          if link not in vagas_unicas:
            vagas_unicas[link] = {
                "titulo": titulo,
                "empresa": "Remotar",
                "local": "Remoto (Home Office)",
                "link": link,
                "minutos": minutos,
                "publicada": rotulo,
            }

        print(
            f"   📄 {len(coletadas)} vagas coletadas na lista,"
            f" {aceitas} passaram nos filtros"
            f" (cortadas: {cortes})"
        )
        if aceitas == 0:
          page.screenshot(path=f"debug_{termo.replace(' ', '_')}.png")

      except Exception as e:
        print(f"⚠️ Erro ao buscar pelo termo '{termo}': {e}")

    # 📅 Vagas sem "X atrás" no card: abre a página da vaga e lê a data
    pendentes = [v for v in vagas_unicas.values() if v["minutos"] == SEM_TEMPO]
    if pendentes:
      print(f"📅 Buscando data de {len(pendentes)} vaga(s) sem tempo no card...")
      pagina_vaga = browser.new_page()
      for v in pendentes:
        try:
          pagina_vaga.goto(
              v["link"], timeout=45000, wait_until="domcontentloaded"
          )
          pagina_vaga.wait_for_timeout(2500)
          minutos, rotulo = extrair_data_atualizacao(
              pagina_vaga.inner_text("body")
          )
          if minutos is not None:
            v["minutos"], v["publicada"] = minutos, rotulo
        except Exception as e:
          print(f"   ⚠️ Não consegui ler a data de {v['link']}: {e}")
      pagina_vaga.close()

    browser.close()

  # Mais recentes primeiro (as sem data ficam no fim)
  lista_final = sorted(vagas_unicas.values(), key=lambda v: v["minutos"])
  print(
      f"✅ Total consolidado de vagas reais e únicas encontradas para você:"
      f" {len(lista_final)}"
  )
  return lista_final


def enviar_email_vagas(
    destinatario_nome, destinatario_email, vagas_encontradas, mensagem_boas_vindas
):
  """Monta o e-mail em HTML estilizado e envia para você."""
  if not vagas_encontradas:
    print(f"ℹ️ Nenhuma vaga nova encontrada hoje para {destinatario_nome}.")
    return

  if not (EMAIL_REMETENTE and SENHA_APP and destinatario_email):
    print("❌ Credenciais de e-mail ausentes no arquivo de configuração.")
    return

  html_conteudo = f"""
    <html>
      <head>
        <style>
          body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.5; }}
          .vaga {{
            border-left: 4px solid #0066cc;
            padding-left: 12px;
            margin-bottom: 25px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
          }}
          .titulo {{ font-size: 16px; font-weight: bold; color: #0066cc; margin-bottom: 4px; }}
          .empresa {{ font-size: 13px; color: #555; margin-bottom: 6px; }}
          .link {{ font-size: 13px; }}
        </style>
      </head>
      <body>
        <h2>🎯 Radar de Vagas Remotas (Remotar)</h2>
        <p>{mensagem_boas_vindas}</p>
        <hr style="border: 0; border-top: 1px solid #ccc; margin-bottom: 20px;">
    """

  for vaga in vagas_encontradas:
    html_conteudo += f"""
        <div class="vaga">
          <div class="titulo">{vaga['titulo']}</div>
          <div class="empresa">🏢 {vaga['empresa']} &nbsp;|&nbsp; 📍 {vaga['local']} &nbsp;|&nbsp; ⏱️ {vaga['publicada']}</div>
          <div class="link"><a href="{vaga['link']}" target="_blank">Acessar Vaga / Candidatar-se</a></div>
        </div>
        """

  html_conteudo += """
        <hr style="border: 0; border-top: 1px solid #ccc; margin-top: 20px;">
        <p style="font-size: 11px; color: #888;">Bot automatizado rodando via Python.</p>
      </body>
    </html>
    """

  msg = MIMEMultipart("alternative")
  msg["Subject"] = (
      f"🚀 {len(vagas_encontradas)} Nova(s) Vaga(s) Encontrada(s) pelo Bot"
  )
  msg["From"] = EMAIL_REMETENTE
  msg["To"] = destinatario_email
  msg.attach(MIMEText(html_conteudo, "html"))

  try:
    print(f"Conectando ao SMTP para enviar e-mail para {destinatario_email}...")
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_REMETENTE, SENHA_APP)
    server.sendmail(EMAIL_REMETENTE, destinatario_email, msg.as_string())
    server.quit()
    print(f"✅ E-mail enviado com sucesso para {destinatario_email}!")
  except Exception as e:
    print(f"❌ Erro ao enviar o e-mail: {e}")


if __name__ == "__main__":
  print("\n--- Buscando vagas para o Sérgio ---")
  vagas_sergio = buscar_e_consolidar_vagas_sergio(
      PERFIL_SERGIO["palavras_chave"]
  )
  enviar_email_vagas(
      destinatario_nome=PERFIL_SERGIO["nome"],
      destinatario_email=PERFIL_SERGIO["email"],
      vagas_encontradas=vagas_sergio,
      mensagem_boas_vindas=PERFIL_SERGIO["mensagem_boas_vindas"],
  )
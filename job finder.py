import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright

# Configurações de Acesso
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_REMETENTE = "saf.salles@gmail.com"
SENHA_APP = "tfnh xfpl yohj fyam"

# Palavras-chave focadas no seu perfil (Dados, BI, Python, etc.)
PALAVRAS_CHAVE = [
    "dados",
    "bi",
    "analista",
    "analytics",
    "engenheiro",
    "python",
    "sql",
]


def buscar_vagas_remotar():
  """Usa o Playwright com seletores nativos para extrair vagas do Remotar."""
  print("Iniciando navegador com Playwright...")
  vagas_encontradas = []

  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("Acessando o site do Remotar...")
    page.goto("https://remotar.com.br/", timeout=60000)

    print("Aguardando carregamento da página...")
    page.wait_for_timeout(5000)

    # Coleta todos os elementos de link da página
    links = page.query_selector_all("a")
    print(f"Analisando {len(links)} links encontrados na página...")

    vistas = set()
    for el in links:
      try:
        titulo = el.inner_text().strip()
        link = el.get_attribute("href")

        if not titulo or not link or len(titulo) < 5 or "#" in link:
          continue

        # Limpa o título pegando apenas a primeira linha
        titulo_limpo = titulo.split("\n")[0]

        # Ajusta links relativos se houver
        if link.startswith("/"):
          link = f"https://remotar.com.br{link}"

        if link in vistas:
          continue
        vistas.add(link)

        # Aplica o filtro de palavras-chave
        titulo_lower = titulo_limpo.lower()
        if any(termo in titulo_lower for termo in PALAVRAS_CHAVE):
          vagas_encontradas.append({
              "titulo": titulo_limpo,
              "empresa": "Remotar",
              "local": "Remoto (Home Office)",
              "link": link,
          })
      except Exception:
        continue

    browser.close()

  print(f"✅ Encontradas {len(vagas_encontradas)} vagas compatíveis com o perfil.")
  return vagas_encontradas


def enviar_email_vagas(vagas_encontradas):
  """Função que monta o e-mail em HTML estilizado e envia para o destinatário."""
  if not vagas_encontradas:
    print("ℹ️ Nenhuma vaga nova encontrada hoje para enviar por e-mail.")
    return

  # HTML com espaçamento melhorado e títulos em destaque
  html_conteudo = """
    <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; color: #333; line-height: 1.5; }
          .vaga { 
            border-left: 4px solid #0066cc; 
            padding-left: 12px; 
            margin-bottom: 25px; 
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
          }
          .titulo { font-size: 16px; font-weight: bold; color: #0066cc; margin-bottom: 4px; }
          .empresa { font-size: 13px; color: #555; margin-bottom: 6px; }
          .link { font-size: 13px; }
        </style>
      </head>
      <body>
        <h2>🎯 Radar de Vagas Remotas (Remotar)</h2>
        <p>Fala, Sérgio! Encontrei estas oportunidades alinhadas ao seu perfil:</p>
        <hr style="border: 0; border-top: 1px solid #ccc; margin-bottom: 20px;">
    """

  for vaga in vagas_encontradas:
    html_conteudo += f"""
        <div class="vaga">
          <div class="titulo">{vaga['titulo']}</div>
          <div class="empresa">🏢 {vaga['empresa']} &nbsp;|&nbsp; 📍 {vaga['local']}</div>
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
  msg["To"] = "saf.salles@gmail.com"
  msg.attach(MIMEText(html_conteudo, "html"))

  try:
    print("Conectando ao servidor do Gmail para envio...")
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_REMETENTE, SENHA_APP)
    server.sendmail(EMAIL_REMETENTE, "saf.salles@gmail.com", msg.as_string())
    server.quit()
    print("✅ E-mail enviado com sucesso para saf.salles@gmail.com!")
  except Exception as e:
    print(f"❌ Erro ao enviar o e-mail: {e}")


if __name__ == "__main__":
  vagas = buscar_vagas_remotar()
  enviar_email_vagas(vagas)
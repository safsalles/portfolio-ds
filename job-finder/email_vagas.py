"""Monta o e-mail em HTML, com as vagas em ordem de prioridade, e envia
pelo Gmail."""

import html
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from classificacao import (LOCAL_CONFERIR, ORDEM_CATEGORIAS, P_FUTEBOL, P_GRANDE,
                           P_MEH, P_OUTRAS, P_QUERO)
from empresas import QUERO_MUITO

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

BLOCOS = {
    P_FUTEBOL: ("⚽ Futebol", "#1a7f37"),
    P_QUERO: ("⭐ Empresas que você quer", "#b8860b"),
    P_GRANDE: ("🏢 Grandes empresas", "#0066cc"),
    P_OUTRAS: ("📋 Outras vagas", "#666666"),
    P_MEH: ("😐 Empresas meh", "#999999"),
}

ESTILO = """
  body { font-family: Arial, sans-serif; color: #333; line-height: 1.5; }
  h3 { margin: 28px 0 8px; padding-bottom: 4px; border-bottom: 2px solid; }
  h4 { margin: 16px 0 8px; color: #555; font-size: 14px; }
  .vaga { border-left: 4px solid; padding-left: 12px; margin-bottom: 18px; }
  .titulo { font-size: 15px; font-weight: bold; }
  .info { font-size: 13px; color: #555; }
  .aviso { font-size: 12px; color: #b35900; }
  .link { font-size: 13px; }
  .sobre { font-size: 12px; color: #777; font-style: italic; }
  .skills { font-size: 12px; color: #777; }
  .afinidade { font-weight: normal; font-size: 13px; }
  .avaliar { font-size: 12px; font-family: Consolas, monospace; color: #444; }
"""


def _e(texto):
  return html.escape(str(texto or ""))


def _afinidade(v):
  """(72%) depois do título e, embaixo, o que a vaga pede que você não tem."""
  if not v.get("afinidade"):
    return "", ""
  porcentagem, _, faltam = v["afinidade"]
  titulo = f" <span class='afinidade'>({porcentagem}% de afinidade)</span>"
  linha = f"<div class='skills'>Falta: {_e(', '.join(faltam))}</div>" if faltam else ""
  return titulo, linha


def montar_html(vagas, mensagem, para_avaliar=None):
  partes = [f"<html><head><style>{ESTILO}</style></head><body>",
            "<h2>Radar de Vagas</h2>", f"<p>{_e(mensagem)}</p>"]
  resumo = [f"{sum(1 for v in vagas if v['prioridade'] == p)} {nome.split(' ', 1)[1].lower()}"
            for p, (nome, _) in BLOCOS.items()]
  partes.append(f"<p class='info'>{len(vagas)} vagas novas: {', '.join(resumo)}.</p>")

  for prioridade, (nome_bloco, cor) in BLOCOS.items():
    do_bloco = [v for v in vagas if v["prioridade"] == prioridade]
    if not do_bloco:
      continue
    partes.append(f"<h3 style='color:{cor}; border-color:{cor}'>{nome_bloco}"
                  f" ({len(do_bloco)})</h3>")
    for categoria in ORDEM_CATEGORIAS:
      da_categoria = [v for v in do_bloco if v["categoria"] == categoria]
      if not da_categoria:
        continue
      if prioridade != 0:  # no bloco de futebol a categoria é sempre a mesma
        partes.append(f"<h4>{_e(categoria)} ({len(da_categoria)})</h4>")
      for v in da_categoria:
        local = " · ".join(x for x in (v["grupo_local"], v["local"]) if x)
        aviso = ""
        if v["grupo_local"] == LOCAL_CONFERIR:
          aviso = ("<div class='aviso'>A vaga é remota mas não diz de que"
                   " países aceita candidatos. Confira antes de se candidatar.</div>")
        afinidade, faltam = _afinidade(v)
        estrela = "⭐ " if v.get("nota") == QUERO_MUITO else ""
        sobre = (f"<div class='sobre'>{_e(v['sobre_empresa'])}</div>"
                 if v.get("sobre_empresa") else "")
        partes.append(f"""
          <div class="vaga" style="border-color:{cor}">
            <div class="titulo" style="color:{cor}">{estrela}{_e(v['titulo'])}{afinidade}</div>
            <div class="info">{_e(v['empresa'] or 'Empresa não informada')} &nbsp;|&nbsp;
              {_e(local)} &nbsp;|&nbsp; {_e(v['publicada'])} &nbsp;|&nbsp; via {_e(v['fonte'])}</div>
            {faltam}{aviso}
            <div class="link"><a href="{_e(v['link'])}" target="_blank">Acessar vaga / Candidatar-se</a></div>
            {sobre}
          </div>""")

  if para_avaliar:
    partes.append("<h3 style='color:#555; border-color:#555'>📝 Empresas novas para você avaliar"
                  f" ({len(para_avaliar)})</h3>"
                  "<p class='info'>Copie as linhas para o <b>empresas.txt</b> e troque o"
                  " <b>ok</b> pela sua nota: quero muito, quero, ok, meh ou evitar.</p>")
    partes.append("<div class='avaliar'>" + "<br>".join(_e(l) for l in para_avaliar) + "</div>")

  partes.append("<hr><p style='font-size:11px;color:#888'>Bot automatizado rodando via Python.</p>")
  partes.append("</body></html>")
  return "".join(partes)


def assunto(vagas):
  futebol = sum(1 for v in vagas if v["prioridade"] == P_FUTEBOL)
  texto = f"{len(vagas)} vaga(s) nova(s)"
  if futebol:
    texto = f"⚽ {futebol} de futebol | {texto} no total"
  return f"Radar de Vagas: {texto}"


def enviar(vagas, mensagem, remetente, senha_app, destinatario, para_avaliar=None):
  if not vagas:
    print("Nenhuma vaga nova hoje, e-mail não enviado.")
    return False
  if not (remetente and senha_app and destinatario):
    print("Credenciais de e-mail ausentes no arquivo de configuração.")
    return False

  msg = MIMEMultipart("alternative")
  msg["Subject"] = assunto(vagas)
  msg["From"] = remetente
  msg["To"] = destinatario
  msg.attach(MIMEText(montar_html(vagas, mensagem, para_avaliar), "html", "utf-8"))
  try:
    print(f"Enviando e-mail para {destinatario}...")
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
      server.starttls()
      server.login(remetente, senha_app)
      server.sendmail(remetente, destinatario, msg.as_string())
    print("E-mail enviado!")
    return True
  except Exception as e:
    print(f"Erro ao enviar o e-mail: {e}")
    return False

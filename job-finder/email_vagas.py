"""Monta o e-mail em HTML, com as vagas em ordem de prioridade, e envia
pelo Gmail."""

import html
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from classificacao import (LOCAL_CONFERIR, ORDEM_CATEGORIAS, P_FUTEBOL, P_GRANDE,
                           P_MEH, P_OUTRAS, P_QUERO)
from empresas import QUERO_MUITO
import respostas

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
  .acoes { font-size: 12px; margin-top: 2px; }
  .acoes a { color: #777; text-decoration: none; margin-right: 12px; }
  .feita { font-size: 13px; color: #555; margin-bottom: 6px; }
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


def montar_html(vagas, mensagem, para_avaliar=None, responder=None, ja_candidatadas=None):
  partes = [f"<html><head><style>{ESTILO}</style></head><body>",
            "<h2>Radar de Vagas</h2>", f"<p>{_e(mensagem)}</p>"]
  resumo = [f"{sum(1 for v in vagas if v['prioridade'] == p)} {nome.split(' ', 1)[1].lower()}"
            for p, (nome, _) in BLOCOS.items()]
  novas = sum(1 for v in vagas if v.get("nova"))
  partes.append(f"<p class='info'>{len(vagas)} vagas abertas ({novas} 🆕 novas desde o último"
                f" e-mail): {', '.join(resumo)}.</p>")

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
        partes.append(_html_vaga(v, cor, local, aviso, responder))

  _fechar(partes, para_avaliar, ja_candidatadas, responder)
  return "".join(partes)


ROTULOS_RESPOSTA = ((respostas.CANDIDATEI, "✅ Já me candidatei"),
                    (respostas.DESCARTAR, "🚫 Descartar"),
                    (respostas.NUNCA_MAIS, "⛔ Nunca mais essa empresa"))


def _links_resposta(v, responder):
  """Os links que abrem um e-mail de resposta pronto (só enviar)."""
  if not responder:
    return ""
  links = [f'<a href="{_e(respostas.link_resposta(acao, v, responder))}">{rotulo}</a>'
           for acao, rotulo in ROTULOS_RESPOSTA
           if acao != respostas.NUNCA_MAIS or v["empresa"]]
  return "<div class='acoes'>" + "".join(links) + "</div>"


def _html_vaga(v, cor, local, aviso="", responder=None):
  afinidade, faltam = _afinidade(v)
  acoes = _links_resposta(v, responder)
  estrela = "⭐ " if v.get("nota") == QUERO_MUITO else ""
  sobre = (f"<div class='sobre'>{_e(v['sobre_empresa'])}</div>"
           if v.get("sobre_empresa") else "")
  return f"""
    <div class="vaga" style="border-color:{cor}">
      <div class="titulo" style="color:{cor}">{estrela}{'🆕 ' if v.get('nova') else ''}{_e(v['titulo'])}{afinidade}</div>
      <div class="info">{_e(v['empresa'] or 'Empresa não informada')} &nbsp;|&nbsp;
        {_e(local)} &nbsp;|&nbsp; {_e(v['publicada'])} &nbsp;|&nbsp; via {_e(v['fonte'])}</div>
      {faltam}{aviso}
      <div class="link"><a href="{_e(v['link'])}" target="_blank">Acessar vaga / Candidatar-se</a></div>
      {acoes}{sobre}
    </div>"""


ROTULOS_NOTA = (("quero muito", "⭐ Quero muito"), ("quero", "👍 Quero"),
                ("ok", "✔ Ok"), ("meh", "😐 Meh"), ("evitar", "⛔ Evitar"))


def _html_empresa(linha, responder):
  """Uma empresa para avaliar: nome, o que ela faz e os links de nota.
  `linha` vem como "Nome | ok | descrição"."""
  partes = [p.strip() for p in linha.split("|", 2)]
  nome = partes[0]
  sobre = f"<div class='sobre'>{_e(partes[2])}</div>" if len(partes) > 2 and partes[2] else ""
  links = "".join(f'<a href="{_e(respostas.link_nota(nota, nome, responder))}">{rotulo}</a>'
                  for nota, rotulo in ROTULOS_NOTA)
  return (f"<div class='feita'><b>{_e(nome)}</b>{sobre}"
          f"<div class='acoes'>{links}</div></div>")


def _html_candidatadas(lista):
  partes = ["<h3 style='color:#1a7f37; border-color:#1a7f37'>✅ Já me candidatei"
            f" ({len(lista)})</h3>"]
  for v in lista:
    dia = "/".join(reversed(v["data"].split("-")[1:]))
    titulo = _e(v["titulo"])
    if v.get("link"):
      titulo = f"<a href=\"{_e(v['link'])}\" target=\"_blank\">{titulo}</a>"
    partes.append(f"<div class='feita'>{dia} · {titulo} · {_e(v['empresa'] or 'Empresa não informada')}</div>")
  return "".join(partes)


def _fechar(partes, para_avaliar, ja_candidatadas=None, responder=None):
  if ja_candidatadas:
    partes.append(_html_candidatadas(ja_candidatadas))
  if responder:
    partes.append("<p class='info'>Os links ✅ 🚫 ⛔ abrem um e-mail pronto: é só enviar."
                  " Na próxima rodada a vaga sai da lista (ou vai para \"Já me candidatei\"),"
                  " e \"Nunca mais\" esconde todas as vagas da empresa.</p>")
  if para_avaliar:
    partes.append("<h3 style='color:#555; border-color:#555'>📝 Empresas novas para você avaliar"
                  f" ({len(para_avaliar)})</h3>")
    if responder:
      partes.append("<p class='info'>Clique na nota: abre um e-mail pronto, é só enviar."
                    " Na próxima rodada a empresa já entra com a sua nota.</p>")
      partes.extend(_html_empresa(linha, responder) for linha in para_avaliar)
    else:
      partes.append("<p class='info'>Copie as linhas para o <b>empresas.txt</b> e troque o"
                    " <b>ok</b> pela sua nota: quero muito, quero, ok, meh ou evitar.</p>")
      partes.append("<div class='avaliar'>" + "<br>".join(_e(l) for l in para_avaliar) + "</div>")
  partes.append("<hr><p style='font-size:11px;color:#888'>Bot automatizado rodando via Python.</p>")
  partes.append("</body></html>")


# --- E-MAIL "PERTO DE CASA" ---
COR_PERTO = "#7a3e9d"
MODELO_ROTULO = {"presencial": "Presencial", "hibrido": "Híbrido", "": "Presencial ou híbrido"}


def montar_html_perto(vagas, para_avaliar=None, responder=None, ja_candidatadas=None):
  """Vagas presenciais/híbridas nas cidades, em ordem de empresa."""
  partes = [f"<html><head><style>{ESTILO}</style></head><body>",
            "<h2>📍 Perto de casa</h2>"]
  por_cidade = {}
  for v in vagas:
    por_cidade[v["cidade"]] = por_cidade.get(v["cidade"], 0) + 1
  novas = sum(1 for v in vagas if v.get("nova"))
  cidades = ", ".join(f"{n} em {c}" for c, n in por_cidade.items())
  partes.append(f"<p class='info'>{len(vagas)} vagas presenciais ou híbridas"
                f" ({novas} 🆕 novas desde o último e-mail): {cidades}.</p>")
  for v in vagas:
    local = f"{v['cidade']} · {MODELO_ROTULO.get(v['modelo'], v['modelo'])}"
    partes.append(_html_vaga(v, COR_PERTO, local, responder=responder))
  _fechar(partes, para_avaliar, ja_candidatadas, responder)
  return "".join(partes)


def assunto_perto(vagas):
  novas = sum(1 for v in vagas if v.get("nova"))
  return f"📍 Perto de casa: {len(vagas)} vaga(s) em Campos, SJB e Macaé, {novas} nova(s)"


def assunto(vagas):
  futebol = sum(1 for v in vagas if v["prioridade"] == P_FUTEBOL)
  novas = sum(1 for v in vagas if v.get("nova"))
  texto = f"{len(vagas)} vaga(s) aberta(s), {novas} nova(s)"
  if futebol:
    texto = f"⚽ {futebol} de futebol | {texto}"
  return f"Radar de Vagas: {texto}"


def enviar(vagas, mensagem, remetente, senha_app, destinatario, para_avaliar=None,
           ja_candidatadas=None):
  """As respostas vão para o remetente: é a caixa que o bot lê pelo IMAP."""
  corpo = montar_html(vagas, mensagem, para_avaliar, remetente, ja_candidatadas)
  return enviar_html(vagas, assunto(vagas), corpo, remetente, senha_app, destinatario)


def enviar_perto(vagas, remetente, senha_app, destinatario, para_avaliar=None,
                 ja_candidatadas=None):
  corpo = montar_html_perto(vagas, para_avaliar, remetente, ja_candidatadas)
  return enviar_html(vagas, assunto_perto(vagas), corpo, remetente, senha_app, destinatario)


def enviar_html(vagas, titulo, corpo, remetente, senha_app, destinatario):
  if not vagas:
    print("Nenhuma vaga aberta hoje, e-mail não enviado.")
    return False
  if not (remetente and senha_app and destinatario):
    print("Credenciais de e-mail ausentes no arquivo de configuração.")
    return False

  msg = MIMEMultipart("alternative")
  msg["Subject"] = titulo
  msg["From"] = remetente
  msg["To"] = destinatario
  msg.attach(MIMEText(corpo, "html", "utf-8"))
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

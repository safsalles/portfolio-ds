"""Radar de Vagas: busca vagas em várias fontes, classifica por categoria,
prioriza futebol, as empresas que você avaliou bem e as grandes e manda as novas por e-mail.

Uso:
  python job_finder.py               busca, envia o e-mail e guarda as vagas enviadas
  python job_finder.py --sem-email   só busca e salva uma prévia do e-mail em HTML
  python job_finder.py --so-perto    só o e-mail Perto de casa (dá pra juntar com --sem-email)

Cada rodada manda dois e-mails: o Radar de Vagas (remotas) e o Perto de
casa (presenciais e híbridas em Campos dos Goytacazes, São João da Barra e
Macaé).
"""

import argparse
import os
import sys

from playwright.sync_api import sync_playwright

import afinidade
import classificacao
import email_vagas
import empresas
import memoria
import perto_de_casa
import respostas
from classificacao import (MAX_DIAS, PADRAO_FUNCAO_FUTEBOL, categoria_geral, eh_futebol,
                           titulo_excluido, vale_abrir_descricao)
from fontes import (empresas_futebol, glassdoor, gupy, infojobs,
                    jobs_in_football, linkedin, remotar, vagas_com)
from util import normalizar

# --- LEITURA SEGURA DAS CREDENCIAIS FORA DO GITHUB ---
PASTA_PRIVADA = os.path.expanduser(r"~\Desktop\aux portfolio\job finder")
CONFIG_PATH = os.path.join(PASTA_PRIVADA, "config_vagas.txt")
PREVIA_PATH = os.path.join(PASTA_PRIVADA, "previa_email.html")
PREVIA_PERTO_PATH = os.path.join(PASTA_PRIVADA, "previa_perto_de_casa.html")

MENSAGEM = "Fala ai doidão. Dá uma olhada nessas vagas:"

# --- O QUE BUSCAR EM CADA FONTE ---
# Remotar: só vagas remotas. Termos largos, a classificação filtra depois.
TERMOS_REMOTAR = [
    "dados", "bi", "analista", "analytics", "business intelligence",
    "administrativo", "administrative assistant", "administrative analyst",
    "data entry", "data clerk", "engenheiro de produção",
    "engenheiro de planejamento", "futebol",
]

# Gupy: vagas brasileiras (remotas ou não; a classificação decide).
TERMOS_GUPY = [
    "analista de dados", "analista de bi", "business intelligence",
    "assistente administrativo", "analista administrativo",
    "futebol", "analista de desempenho", "scout",
]

# LinkedIn (busca pública): (palavras, região, só remoto, período).
# "Só remoto" é um pedido ao LinkedIn, que nem sempre obedece; o modelo de
# trabalho é conferido depois na descrição de cada vaga.
BUSCAS_LINKEDIN = [
    ("analista de dados", linkedin.BRASIL, True, linkedin.SEMANA),
    ("data analyst", linkedin.BRASIL, True, linkedin.SEMANA),
    ("analista de bi", linkedin.BRASIL, True, linkedin.SEMANA),
    ("assistente administrativo", linkedin.BRASIL, True, linkedin.SEMANA),
    ("futebol", linkedin.BRASIL, False, linkedin.MES),
    ("scout futebol", linkedin.BRASIL, False, linkedin.MES),
    ("football analyst", linkedin.AMERICA_LATINA, True, linkedin.MES),
    ("football data", linkedin.MUNDO, True, linkedin.MES),
    # Funções operacionais em inglês (Brasil e América Latina; no mundo só
    # as remotas "worldwide"/"anywhere" passam pelo filtro de local).
    ("data entry", linkedin.BRASIL, True, linkedin.SEMANA),
    ("data operator", linkedin.BRASIL, True, linkedin.SEMANA),
    ("administrative assistant", linkedin.BRASIL, True, linkedin.SEMANA),
    ("administrative analyst", linkedin.BRASIL, True, linkedin.SEMANA),
    ("data entry", linkedin.AMERICA_LATINA, True, linkedin.SEMANA),
    ("administrative assistant", linkedin.AMERICA_LATINA, True, linkedin.SEMANA),
    ("administrative analyst", linkedin.AMERICA_LATINA, True, linkedin.SEMANA),
    ("data entry remote", linkedin.MUNDO, True, linkedin.SEMANA),
    ("administrative assistant remote", linkedin.MUNDO, True, linkedin.SEMANA),
    ("soccer analyst", linkedin.MUNDO, True, linkedin.MES),
]

TERMOS_JOBS_IN_FOOTBALL = ["analyst", "data", "scout", "analytics"]

# Termos das vagas gerais, usados no Glassdoor, InfoJobs e Vagas.com.
TERMOS_GERAIS = [
    "analista de dados", "analista de bi", "business intelligence",
    "assistente administrativo", "analista administrativo",
]
TERMOS_GLASSDOOR = TERMOS_GERAIS + ["futebol"]  # só remotas (filtro do site)
TERMOS_INFOJOBS = TERMOS_GERAIS + ["futebol"]
TERMOS_VAGAS_COM = TERMOS_GERAIS + ["futebol", "analista de desempenho"]


# Cada descrição do LinkedIn é um pedido a mais (com pausa); o limite evita
# que o LinkedIn bloqueie e que a rodada demore demais.
MAX_DESCRICOES_LINKEDIN = 70
# O Vagas.com não diz na lista se a vaga é remota: abre a página das que
# podem servir, até este limite por rodada.
MAX_DESCRICOES_VAGAS_COM = 40


def carregar_config():
  config = {}
  try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
      for linha in f:
        if "=" in linha and not linha.startswith("#"):
          chave, valor = linha.strip().split("=", 1)
          config[chave.strip()] = valor.strip()
    print("Credenciais carregadas com segurança do arquivo externo!")
  except Exception as e:
    print(f"Erro ao ler o arquivo de configuração em {CONFIG_PATH}: {e}")
  return config


def funcao_de_futebol(titulo):
  return bool(PADRAO_FUNCAO_FUTEBOL.search(normalizar(titulo)))


def coletar_sem_navegador():
  vagas = []
  print("\n[1/5] Empresas de dados de futebol")
  vagas += empresas_futebol.buscar()
  print("\n[2/5] Gupy")
  vagas += gupy.buscar(TERMOS_GUPY)
  print("\n[3/5] LinkedIn (busca pública)")
  do_linkedin = linkedin.buscar(BUSCAS_LINKEDIN)
  # A lista do LinkedIn não diz se a vaga é remota: abre a descrição das que
  # podem entrar no e-mail (futebol primeiro, até o limite por rodada).
  para_abrir = sorted((v for v in do_linkedin if vale_abrir_descricao(v)),
                      key=lambda v: not eh_futebol(v))[:MAX_DESCRICOES_LINKEDIN]
  print(f"   LinkedIn: lendo a descrição de {len(para_abrir)} vagas")
  for vaga in para_abrir:
    if not linkedin.completar_descricao(vaga):
      vaga["encerrada"] = True
  vagas += [v for v in do_linkedin if not v.get("encerrada")]

  print("\n[4/5] Vagas.com")
  do_vagas_com = vagas_com.buscar(TERMOS_VAGAS_COM)
  para_abrir = [v for v in do_vagas_com
                if not eh_futebol(v) and categoria_geral(v["titulo"])
                and not titulo_excluido(v["titulo"]) and v["minutos"] <= MAX_DIAS * 1440]
  para_abrir = sorted(para_abrir, key=lambda v: v["minutos"])[:MAX_DESCRICOES_VAGAS_COM]
  print(f"   Vagas.com: lendo a descrição de {len(para_abrir)} vagas")
  for n, vaga in enumerate(para_abrir):
    if not vagas_com.completar_descricao(vaga):
      print(f"   Vagas.com: o site recusou depois de {n} páginas, parando por hoje")
      break
  vagas += do_vagas_com
  return vagas


def main():
  parser = argparse.ArgumentParser(description=__doc__,
                                   formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("--sem-email", action="store_true",
                      help="não envia e-mail nem guarda as vagas; salva uma prévia em HTML")
  parser.add_argument("--so-perto", action="store_true",
                      help="roda só o e-mail Perto de casa (Campos, SJB e Macaé)")
  args = parser.parse_args()

  config = carregar_config()
  empresas_grandes = classificacao.carregar_empresas_grandes()
  avaliacoes = empresas.carregar()
  minhas = afinidade.minhas_competencias()
  print(f"{len(empresas_grandes)} grandes empresas na lista, {len(avaliacoes)} avaliadas por você,"
        f" {len(minhas)} competências suas para a afinidade")
  vistas = memoria.carregar()
  # Respostas ao e-mail (já me candidatei / descartar / nunca mais essa empresa).
  estado = respostas.carregar()
  respostas.ler_respostas(estado, config.get("EMAIL_REMETENTE"), config.get("SENHA_APP"),
                          config.get("MEU_EMAIL"))
  respostas.evitar_empresas(estado, avaliacoes)
  enviadas = []

  if not args.so_perto:
    enviadas += radar(args, config, empresas_grandes, avaliacoes, minhas, vistas, estado)
  enviadas += perto(args, config, avaliacoes, minhas, vistas, estado)

  if enviadas:
    memoria.salvar(enviadas, vistas)
    print(f"{len(enviadas)} vagas guardadas em {memoria.CAMINHO}")
  if not args.sem_email:
    respostas.salvar(estado)
  return 0


def marcar_novas(vagas, vistas):
  """O e-mail traz TODAS as vagas abertas, não só as novas (nem todo dia dá
  pra ler). A memória só serve pra marcar quais são novidade."""
  for v in vagas:
    v["nova"] = not any(k in vistas for k in memoria.chaves(v))


def salvar_previa(caminho, html):
  os.makedirs(PASTA_PRIVADA, exist_ok=True)
  with open(caminho, "w", encoding="utf-8") as f:
    f.write(html)
  print(f"\nPrévia do e-mail salva em {caminho} (nada foi enviado nem guardado)")


def perto(args, config, avaliacoes, minhas, vistas, estado):
  """E-mail Perto de casa. Devolve as vagas enviadas (ou [] em prévia)."""
  print("\n=== PERTO DE CASA ===")
  filtros = perto_de_casa.carregar_filtros()
  vagas = []
  for cidade in perto_de_casa.CIDADES:
    vagas += gupy.buscar_cidade(cidade["gupy"])
    vagas += vagas_com.buscar_cidade(cidade["vagas_com"])
    vagas += linkedin.buscar_cidade(cidade["linkedin"])
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for cidade in perto_de_casa.CIDADES:
      vagas += infojobs.buscar_cidade(cidade["infojobs"], browser)
    browser.close()

  aceitas = perto_de_casa.filtrar(vagas, filtros, avaliacoes)
  aceitas = respostas.tirar_marcadas(aceitas, estado)
  # LinkedIn e Vagas.com não trazem a descrição na lista: abre a página só das
  # que sobraram, pra conferir o que a vaga exige.
  for v in aceitas:
    if not v["descricao"] or len(v["descricao"]) < 600:
      if v["fonte"] == "LinkedIn":
        linkedin.completar_descricao(v)
      elif v["fonte"] == "Vagas.com":
        vagas_com.completar_descricao(v)
  aceitas = perto_de_casa.tirar_por_exigencia(aceitas, filtros)
  marcar_novas(aceitas, vistas)
  afinidade.completar(aceitas, minhas)
  empresas.completar_descricoes(aceitas, avaliacoes)
  para_avaliar = empresas.empresas_para_avaliar(aceitas)
  print(f"   {len(aceitas)} vagas, {sum(v['nova'] for v in aceitas)} novas,"
        f" {len(para_avaliar)} empresas novas para avaliar")

  ja = respostas.candidatadas(estado, "perto")
  if args.sem_email:
    salvar_previa(PREVIA_PERTO_PATH, email_vagas.montar_html_perto(
        aceitas, para_avaliar, config.get("EMAIL_REMETENTE"), ja))
    return []
  enviado = email_vagas.enviar_perto(
      aceitas, config.get("EMAIL_REMETENTE"), config.get("SENHA_APP"),
      config.get("MEU_EMAIL"), para_avaliar, ja)
  if not enviado:
    return []
  respostas.lembrar(estado, aceitas, "perto")
  return aceitas


def radar(args, config, empresas_grandes, avaliacoes, minhas, vistas, estado):
  """E-mail principal. Devolve as vagas enviadas (ou [] em prévia)."""
  vagas = coletar_sem_navegador()

  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    print("\n[5/5] Remotar, Jobs In Football, Glassdoor, InfoJobs (navegador)")
    vagas += remotar.buscar(TERMOS_REMOTAR, browser)
    vagas += glassdoor.buscar(TERMOS_GLASSDOOR, browser)
    vagas += infojobs.buscar(TERMOS_INFOJOBS, browser)
    candidatas = jobs_in_football.buscar(TERMOS_JOBS_IN_FOOTBALL, browser)
    vagas += jobs_in_football.detalhar(candidatas, browser, funcao_de_futebol)

    print(f"\nTotal coletado: {len(vagas)} vagas")
    aceitas = classificacao.classificar(vagas, empresas_grandes, avaliacoes)

    novas = memoria.filtrar_novas(aceitas, {})  # tira repetidas entre fontes
    novas = respostas.tirar_marcadas(novas, estado)
    marcar_novas(novas, vistas)
    print(f"{len(novas)} vagas abertas, {sum(v['nova'] for v in novas)} novas desde o último e-mail")

    remotar.completar_datas(novas, browser)
    browser.close()

  # A página da vaga pode revelar que ela é híbrida/presencial.
  novas = [v for v in novas if v["categoria"] == classificacao.FUTEBOL or v["modelo"] == "remoto"]
  novas = classificacao.ordenar(novas)

  afinidade.completar(novas, minhas)
  print("Procurando a descrição das empresas novas (Wikipédia, com cache)...")
  empresas.completar_descricoes(novas, avaliacoes)
  para_avaliar = empresas.empresas_para_avaliar(novas)

  for prioridade, (nome, _) in email_vagas.BLOCOS.items():
    print(f"   {nome}: {sum(1 for v in novas if v['prioridade'] == prioridade)}")
  print(f"   empresas novas para avaliar: {len(para_avaliar)}")

  ja = respostas.candidatadas(estado, "radar")
  if args.sem_email:
    salvar_previa(PREVIA_PATH, email_vagas.montar_html(
        novas, MENSAGEM, para_avaliar, config.get("EMAIL_REMETENTE"), ja))
    return []
  enviado = email_vagas.enviar(
      novas, MENSAGEM, config.get("EMAIL_REMETENTE"), config.get("SENHA_APP"),
      config.get("MEU_EMAIL"), para_avaliar, ja,
  )
  if not enviado:
    return []
  respostas.lembrar(estado, novas, "radar")
  return novas


if __name__ == "__main__":
  sys.exit(main())

"""Radar de Vagas: busca vagas em várias fontes, classifica por categoria,
prioriza futebol, as empresas que você avaliou bem e as grandes e manda as novas por e-mail.

Uso:
  python job_finder.py               busca, envia o e-mail e guarda as vagas enviadas
  python job_finder.py --sem-email   só busca e salva uma prévia do e-mail em HTML
  python job_finder.py --sem-email --todas
                                     prévia com todas as vagas, até as já enviadas
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
from classificacao import PADRAO_FUNCAO_FUTEBOL, eh_futebol, vale_abrir_descricao
from fontes import empresas_futebol, gupy, jobs_in_football, linkedin, remotar
from util import normalizar

# --- LEITURA SEGURA DAS CREDENCIAIS FORA DO GITHUB ---
PASTA_PRIVADA = os.path.expanduser(r"~\Desktop\aux portfolio\job finder")
CONFIG_PATH = os.path.join(PASTA_PRIVADA, "config_vagas.txt")
PREVIA_PATH = os.path.join(PASTA_PRIVADA, "previa_email.html")

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
    ("soccer analyst", linkedin.MUNDO, True, linkedin.MES),
]

TERMOS_JOBS_IN_FOOTBALL = ["analyst", "data", "scout", "analytics"]

# Cada descrição do LinkedIn é um pedido a mais (com pausa); o limite evita
# que o LinkedIn bloqueie e que a rodada demore demais.
MAX_DESCRICOES_LINKEDIN = 45


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
  print("\n[1/4] Empresas de dados de futebol")
  vagas += empresas_futebol.buscar()
  print("\n[2/4] Gupy")
  vagas += gupy.buscar(TERMOS_GUPY)
  print("\n[3/4] LinkedIn (busca pública)")
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
  return vagas


def main():
  parser = argparse.ArgumentParser(description=__doc__,
                                   formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("--sem-email", action="store_true",
                      help="não envia e-mail nem guarda as vagas; salva uma prévia em HTML")
  parser.add_argument("--todas", action="store_true",
                      help="com --sem-email: inclui as vagas já enviadas antes")
  args = parser.parse_args()
  if args.todas and not args.sem_email:
    parser.error("--todas só funciona junto com --sem-email")

  config = carregar_config()
  empresas_grandes = classificacao.carregar_empresas_grandes()
  avaliacoes = empresas.carregar()
  minhas = afinidade.minhas_competencias()
  print(f"{len(empresas_grandes)} grandes empresas na lista, {len(avaliacoes)} avaliadas por você,"
        f" {len(minhas)} competências suas para a afinidade")

  vagas = coletar_sem_navegador()

  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    print("\n[4/4] Remotar e Jobs In Football (navegador)")
    vagas += remotar.buscar(TERMOS_REMOTAR, browser)
    candidatas = jobs_in_football.buscar(TERMOS_JOBS_IN_FOOTBALL, browser)
    vagas += jobs_in_football.detalhar(candidatas, browser, funcao_de_futebol)

    print(f"\nTotal coletado: {len(vagas)} vagas")
    aceitas = classificacao.classificar(vagas, empresas_grandes, avaliacoes)

    vistas = memoria.carregar()
    novas = aceitas if args.todas else memoria.filtrar_novas(aceitas, vistas)
    print(f"{len(novas)} vagas novas (as outras já foram enviadas antes)")

    # Só agora abre as páginas do Remotar sem data, e só das vagas novas.
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

  if args.sem_email:
    os.makedirs(PASTA_PRIVADA, exist_ok=True)
    with open(PREVIA_PATH, "w", encoding="utf-8") as f:
      f.write(email_vagas.montar_html(novas, MENSAGEM, para_avaliar))
    print(f"\nPrévia do e-mail salva em {PREVIA_PATH} (nada foi enviado nem guardado)")
    return 0

  enviado = email_vagas.enviar(
      novas, MENSAGEM, config.get("EMAIL_REMETENTE"), config.get("SENHA_APP"),
      config.get("MEU_EMAIL"), para_avaliar,
  )
  if enviado:
    memoria.salvar(novas, vistas)
    print(f"{len(novas)} vagas guardadas em {memoria.CAMINHO}")
  return 0


if __name__ == "__main__":
  sys.exit(main())

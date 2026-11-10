"""Decide a categoria, se a vaga é de futebol, se é de grande empresa e se
o local serve (remoto aceitando Brasil, ou no Brasil)."""

import os
import re

import empresas
from util import SEM_TEMPO, normalizar

# --- PRIORIDADES (blocos do e-mail, nesta ordem) ---
P_FUTEBOL, P_QUERO, P_GRANDE, P_OUTRAS, P_MEH = 0, 1, 2, 3, 4

# --- CATEGORIAS (a ordem aqui é a ordem no e-mail) ---
FUTEBOL = "Analytics Futebol"
DADOS = "Análise de Dados"
BI = "Analista de BI"
ADMIN = "Analista/Assistente Administrativo"
OUTRAS = "Outras (Engenharia de Produção/Planejamento)"
ORDEM_CATEGORIAS = [FUTEBOL, DADOS, BI, ADMIN, OUTRAS]

# Padrões procurados no título (já sem acento e minúsculo).
# A primeira categoria que casar vence, então BI vem antes de Dados:
# "Analista de BI e Dados" é mais BI do que dados.
PADROES_CATEGORIA = [
    (BI, r"\bbi\b|business intelligence|power ?bi|inteligencia de negocio"),
    (ADMIN, r"administrativ|administrative|data entry|data clerk"
            r"|assistente de escritorio|auxiliar de escritorio|data operator"
            r"|operador de dados"),
    # Bolsas do Instituto Euvaldo Lodi (InfoJobs): o título lista as tecnologias.
    (DADOS, r"bolsista.*(\bsql\b|python|pyspark|machine learning|estatistic)"),
    (DADOS, r"\bdados\b|\bdata\b|analytics|cientista|scientist|estatistic"
            r"|insights?\b|analista de performance|performance analyst"
            r"|\bdatos\b|pricing|precificacao|analista de precios|revenue analyst"),
    (OUTRAS, r"engenheir[oa]\(?a?\)? de (producao|planejamento)"
             r"|production engineer|planning engineer|\bpcp\b"),
]

# Título com algum destes nunca entra (mesmos critérios do bot antigo).
#   "engineer"/"engenheiro" cai fora, menos engenharia de produção/planejamento
#   (categoria Outras), que é testada antes em titulo_excluido().
EXCLUIR_NO_TITULO = re.compile(
    r"estag|\bintern\b|\binternship\b|trainee|\bengineer|engenheir|"
    r"seguranca|arquitet|architect|infraestrutura|ux/ui|ui/ux|"
    r"recrutamento|selecao|fiscal|software|mobile|c\+\+|\bjava\b|devops|"
    r"product manager|gerente de produto|banco de dados|database|bolsista doutor|"
    r"\bgrowth\b|marketing|midia paga|trafego pago|\bads\b"
)

# --- CIÊNCIA E ENGENHARIA DE DADOS, E VAGAS AFIRMATIVAS ---
# O nível só importa para cientista de dados (analista de dados e de BI sênior
# continuam entrando).
# Data science / machine learning só entra em nível de abertura.
CIENCIA_DE_DADOS = re.compile(
    r"data scien|cientista de dados|ciencia de dados|machine learning|"
    r"aprendizado de maquina|\bml\b|\bai\b|inteligencia artificial"
)
NIVEL_DE_ABERTURA = re.compile(r"junior|\bjr\b|entry|associate|\bi$")
# Engenharia de dados não serve (vale também para vagas de futebol).
ENGENHARIA_DE_DADOS = re.compile(
    r"data engineer|engenheir[oa] (\(a\) )?de dados|analytics engineer|"
    r"machine learning engineer|\bml engineer|dataops|data platform engineer"
)
# Vaga exclusiva para PcD ou minorias (você não pode se candidatar).
_QUEM = (r"(pessoas? com deficiencia|\bpcds?\b|mulheres|pessoas? negras?|pretos?|"
         r"lgbt|indigenas?|pessoas? trans|refugiad|50\+|acima de 50)")
EXCLUSIVA_NO_TITULO = re.compile(
    r"\bpcds?\b|pessoas? com deficiencia|vagas? afirmativas?|afirmativa para|"
    r"exclusiv[ao]s? (para|a|de) " + _QUEM
)
EXCLUSIVA_NA_DESCRICAO = re.compile(
    r"vagas? afirmativas?|exclusiv[ao]s? (para|a|de|ao) (candidat[oa]s? )?" + _QUEM + "|"
    r"(somente|apenas|so) para " + _QUEM + "|"
    r"(destinada|reservada|direcionada) (exclusivamente )?(a|para|as) " + _QUEM + "|"
    r"exclusively for " + _QUEM
)


def nivel_nao_serve(titulo):
  """Motivo (texto) se o nível do título não serve, ou None."""
  t = normalizar(titulo)
  if ENGENHARIA_DE_DADOS.search(t):
    return "engenharia de dados"
  # Bolsa de pesquisa é vaga de abertura, mesmo sendo de ciência de dados.
  if (CIENCIA_DE_DADOS.search(t) and not NIVEL_DE_ABERTURA.search(t)
      and "bolsista" not in t):
    return "data science só em nível de abertura"
  return None


def exclusiva_para_minorias(titulo, descricao=""):
  if EXCLUSIVA_NO_TITULO.search(normalizar(titulo)):
    return True
  return bool(EXCLUSIVA_NA_DESCRICAO.search(normalizar(descricao)))


# Vagas com data mais antiga que isso são ignoradas (algumas fontes mantêm
# vagas de anos atrás no ar).
MAX_DIAS = 45
# Bolsas de pesquisa (Instituto Euvaldo Lodi) ficam abertas por meses.
MAX_DIAS_BOLSA = 120


def antiga(vaga):
  if vaga["minutos"] == SEM_TEMPO:
    return False
  limite = MAX_DIAS_BOLSA if "bolsista" in normalizar(vaga["titulo"]) else MAX_DIAS
  return vaga["minutos"] > limite * 1440


# --- FUTEBOL ---
# Empresas cujo negócio é futebol/dados esportivos.
EMPRESAS_DE_FUTEBOL = [
    "hudl", "statsbomb", "wyscout", "stats perform", "opta", "genius sports",
    "sportradar", "kitman labs", "catapult", "skillcorner", "scisports",
    "twenty3", "kognia", "footstats", "teamworks", "swish analytics",
    "smarterscout", "analytics fc", "transferroom", "sofascore", "fotmob",
    "cbf", "confederacao brasileira de futebol", "federacao paulista de futebol",
    "federacao de futebol", "conmebol", "fifa", "uefa", "premier league",
    "major league soccer", "pluto data analytics",
    "360 scouting", "scout-live",
]

# Palavras no título/empresa que indicam futebol.
PADRAO_FUTEBOL = re.compile(
    r"futebol|football|soccer|\bscout|scouting|\bfc\b|\bf\.c\.|"
    r"futebol clube|esporte clube|sport club|athletico|atletico|"
    r"\bsaf\b|recruitment analyst|opposition analys|analise de desempenho|"
    r"analista de desempenho|analista de mercado.*futebol"
)

# "Football" nos EUA costuma ser futebol americano.
PADRAO_NAO_E_FUTEBOL = re.compile(
    r"american football|\bnfl\b|college football|fantasy|flag football"
)

# Funções de futebol que interessam (o resto, tipo chef ou vendas, cai fora).
#   "performance" e "video" sozinhos ficam de fora: pegavam "Performance
#   Chef" e "Video Social Producer". "Performance Analyst" entra por "analy".
PADRAO_FUNCAO_FUTEBOL = re.compile(
    r"analy|analis|\bdata\b|\bdados\b|scout|insight|scien|cientist|"
    r"intelligence|\bbi\b|estatistic|statistic|research|pesquisa|\bmodel|"
    r"data collect|data operat|football operations|match (data|report)"
)

# --- LOCAL ---
PADRAO_BRASIL = re.compile(r"\bbrazil\b|\bbrasil\b")
PADRAO_REMOTO = re.compile(r"remot|home office|work from home|anywhere")
PADRAO_ACEITA_BRASIL = re.compile(
    r"\bbrazil\b|\bbrasil\b|latam|latin america|america latina|south america|"
    r"america do sul|anywhere|worldwide|work from anywhere|fully remote globally|"
    r"any country|global remote|remote.{0,20}global"
)
PADRAO_RESTRITO = re.compile(
    r"(based|located|reside|residing|resident|living) in (the )?"
    r"(us|u\.s\.|usa|united states|uk|united kingdom|europe|eu|canada)\b|"
    r"(right|authori[sz]ed|eligible|permission) to (live and )?work in (the )?"
    r"(us|u\.s\.|united states|uk|united kingdom|eu|europe|canada)|"
    r"\b(us|uk|eu)[- ]only|not eligible for sponsorship|"
    r"(unable|not able) to (offer|provide) (visa )?sponsorship|"
    r"remote candidates in the (uk|us)|candidates currently based in"
)

# Grupos de local mostrados no e-mail para vagas de futebol.
LOCAL_REMOTO_OK = "Remoto (aceita Brasil)"
LOCAL_BRASIL = "No Brasil"
LOCAL_CONFERIR = "Remoto, confira se aceita Brasil"


def _contem_algum(texto_norm, termos):
  return any(re.search(rf"(^|\W){re.escape(t)}($|\W)", texto_norm) for t in termos)


def titulo_excluido(titulo):
  if categoria_geral(titulo) == OUTRAS:
    return False
  return bool(EXCLUIR_NO_TITULO.search(normalizar(titulo)))


# Modelo de trabalho escrito na descrição. Híbrido e presencial são testados
# antes de remoto: "remote flex days" numa vaga 4 dias no escritório é híbrida.
_HIBRIDO = re.compile(r"hibrid|hybrid")
_BENEFICIO_HOME = re.compile(
    r"(auxilio|ajuda de custo|verba|vale|bonus|beneficio|stipend|allowance)"
    r"\s*(de |para |-)?\s*home ?office|home ?office\s*(allowance|stipend)")
_PRESENCIAL = re.compile(
    r"100% presencial|modalidade:? presencial|modelo de trabalho:? presencial|"
    r"trabalho presencial|atuacao presencial|\bon-?site\b|in[- ]office|"
    r"office.{0,30}(\d|four|five|three) days a week"
)
_REMOTO = re.compile(
    r"100% remot|totalmente remot|trabalho remoto|modalidade:? remot|"
    r"modelo de trabalho:? remot|home ?office|fully remote|remote[- ]first|"
    r"\bremote (role|position|job|work|opportunity)|(role|position|job) is remote|"
    r"work from (home|anywhere)|\bremot[eo]\b"
)


def modelo_pela_descricao(titulo, local, descricao):
  """'remoto', 'hibrido', 'presencial' ou '' lendo título, local e descrição."""
  topo = normalizar(f"{titulo} {local}")
  if re.search(r"\bremot[eo]\b|home office|work from home", topo):
    return "remoto"
  if _HIBRIDO.search(topo):
    return "hibrido"
  # "Auxílio home office: R$ 200" é benefício, não o modelo da vaga.
  texto = _BENEFICIO_HOME.sub("", normalizar(descricao))
  if _HIBRIDO.search(texto):
    return "hibrido"
  if _PRESENCIAL.search(texto):
    return "presencial"
  if _REMOTO.search(texto):
    return "remoto"
  return ""


# Local que não amarra a vaga a um país: vazio, só "Remote", ou uma região
# ampla ("LATAM", "Worldwide"). "Remote - Estonia" não é genérico.
_REGIAO_AMPLA = re.compile(
    r"latam|latin america|america latina|americas|south america|america do sul|"
    r"anywhere|worldwide|global"
)


def local_generico(local_norm):
  if _REGIAO_AMPLA.search(local_norm):
    return True
  return re.sub(r"remote|remoto|[\s\-(),/]", "", local_norm) == ""


def categoria_geral(titulo):
  """Categoria pelo título, ou None se não for nenhuma das que interessam."""
  t = normalizar(titulo)
  for categoria, padrao in PADROES_CATEGORIA:
    if re.search(padrao, t):
      return categoria
  return None


def eh_futebol(vaga):
  """True se a vaga é de futebol e de uma função que interessa."""
  titulo = normalizar(vaga["titulo"])
  empresa = normalizar(vaga["empresa"])
  texto = f"{titulo} {empresa}"
  if PADRAO_NAO_E_FUTEBOL.search(texto):
    return False
  # Clube sem "FC" no nome (ex.: "Manchester United"): a descrição fala de
  # futebol várias vezes.
  descricao = normalizar(vaga["descricao"])
  futebol_na_descricao = (
      not PADRAO_NAO_E_FUTEBOL.search(descricao)
      and len(re.findall(r"futebol|football|soccer", descricao)) >= 2
  )
  do_futebol = (
      vaga.get("fonte_de_futebol")
      or _contem_algum(empresa, EMPRESAS_DE_FUTEBOL)
      or bool(PADRAO_FUTEBOL.search(texto))
      or futebol_na_descricao
  )
  return bool(do_futebol and PADRAO_FUNCAO_FUTEBOL.search(titulo))


def local_futebol(vaga):
  """Para vagas de futebol: devolve o grupo de local, ou None se não serve
  (não é remota, ou é remota só para EUA/Reino Unido/Europa). Vaga de
  futebol também precisa ser remota."""
  local = normalizar(vaga["local"])
  descricao = normalizar(vaga["descricao"])

  if vaga["modelo"] != "remoto":
    return None
  if PADRAO_BRASIL.search(local):
    return LOCAL_BRASIL
  if PADRAO_RESTRITO.search(descricao):
    return None
  # "Aceita Brasil" só quando a vaga não amarra a um país e cita Brasil,
  # LATAM ou anywhere. Remota "em Cochabamba" ou "Remote - Estonia" é local,
  # mesmo que a descrição cite escritórios no Brasil: vai para conferir.
  if local_generico(local) and PADRAO_ACEITA_BRASIL.search(f"{local} {descricao}"):
    return LOCAL_REMOTO_OK
  return LOCAL_CONFERIR


def local_geral_ok(vaga):
  """Vagas gerais: remotas, no Brasil ou sem país definido."""
  local = normalizar(vaga["local"])
  return bool(PADRAO_BRASIL.search(local) or local_generico(local))


def vale_abrir_descricao(vaga):
  """Para fontes sem descrição (LinkedIn): só abre as vagas que podem entrar
  no e-mail, pra fazer poucos pedidos."""
  if vaga["descricao"]:
    return False
  if eh_futebol(vaga):
    return True
  return (categoria_geral(vaga["titulo"]) is not None
          and not titulo_excluido(vaga["titulo"])
          and local_geral_ok(vaga))


# --- GRANDES EMPRESAS ---
ARQUIVO_EMPRESAS = os.path.join(os.path.dirname(__file__), "empresas_grandes.txt")


def carregar_empresas_grandes(caminho=ARQUIVO_EMPRESAS):
  """Lê o arquivo (uma empresa por linha, # é comentário)."""
  nomes = []
  try:
    with open(caminho, "r", encoding="utf-8") as f:
      for linha in f:
        linha = linha.split("#", 1)[0].strip()
        if linha:
          nomes.append(normalizar(linha))
  except FileNotFoundError:
    print(f"Arquivo de grandes empresas não encontrado: {caminho}")
  return nomes


def eh_grande_empresa(empresa, empresas_grandes):
  """Compara por palavra inteira: 'Itaú Unibanco' casa com 'itau'."""
  return _contem_algum(normalizar(empresa), empresas_grandes)


def classificar(vagas, empresas_grandes, avaliacoes=None):
  """Põe categoria, prioridade, grupo de local e a sua nota da empresa em
  cada vaga e descarta as que não interessam.
  Prioridade: futebol > empresas que você quer > grandes > outras > meh.
  Empresa com nota "evitar" sai do e-mail."""
  avaliacoes = avaliacoes or {}
  aceitas = []
  cortes = {"antiga": 0, "título excluído": 0, "fora das categorias": 0,
            "local não serve": 0, "não é remota": 0, "empresa a evitar": 0,
            "empresa confidencial": 0, "nível": 0, "exclusiva PcD/minorias": 0}

  for vaga in vagas:
    aval = empresas.avaliacao(vaga["empresa"], avaliacoes)
    vaga["nota"] = aval["nota"] if aval else None
    if re.search(r"confidencial|confidential", normalizar(vaga["empresa"])):
      cortes["empresa confidencial"] += 1
      continue
    if nivel_nao_serve(vaga["titulo"]):
      cortes["nível"] += 1
      continue
    if exclusiva_para_minorias(vaga["titulo"], vaga["descricao"]):
      cortes["exclusiva PcD/minorias"] += 1
      continue
    if vaga["nota"] == empresas.EVITAR:
      cortes["empresa a evitar"] += 1
      continue

    if antiga(vaga):
      cortes["antiga"] += 1
      continue

    if not vaga["modelo"]:
      vaga["modelo"] = modelo_pela_descricao(vaga["titulo"], vaga["local"], vaga["descricao"])

    if titulo_excluido(vaga["titulo"]) and not eh_futebol(vaga):
      cortes["título excluído"] += 1
      continue

    if eh_futebol(vaga):
      grupo = local_futebol(vaga)
      if grupo is None:
        cortes["local não serve"] += 1
        continue
      vaga.update(categoria=FUTEBOL, prioridade=P_FUTEBOL, grupo_local=grupo)
      aceitas.append(vaga)
      continue

    categoria = categoria_geral(vaga["titulo"])
    if categoria is None:
      cortes["fora das categorias"] += 1
      continue
    if vaga["modelo"] != "remoto":
      cortes["não é remota"] += 1
      continue
    if not local_geral_ok(vaga):
      cortes["local não serve"] += 1
      continue
    # Vaga em inglês "remota" que só aceita gente de certos países.
    if not PADRAO_BRASIL.search(normalizar(vaga["local"])) and         PADRAO_RESTRITO.search(normalizar(vaga["descricao"])):
      cortes["local não serve"] += 1
      continue

    if vaga["nota"] in (empresas.QUERO_MUITO, empresas.QUERO):
      prioridade = P_QUERO
    elif vaga["nota"] == empresas.MEH:
      prioridade = P_MEH
    elif eh_grande_empresa(vaga["empresa"], empresas_grandes):
      prioridade = P_GRANDE
    else:
      prioridade = P_OUTRAS
    vaga.update(categoria=categoria, prioridade=prioridade, grupo_local="Remoto")
    aceitas.append(vaga)

  print(f"Classificação: {len(aceitas)} vagas aceitas (cortadas: {cortes})")
  return aceitas


def ordenar(vagas):
  """Por bloco de prioridade; dentro do bloco, "quero muito" primeiro,
  depois por categoria e das mais recentes para as mais antigas."""
  return sorted(
      vagas,
      key=lambda v: (v["prioridade"], v.get("nota") != empresas.QUERO_MUITO,
                     ORDEM_CATEGORIAS.index(v["categoria"]), v["minutos"]),
  )

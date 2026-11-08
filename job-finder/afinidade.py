"""Afinidade entre as suas competências e a vaga, em %.

Como funciona:
  1. Há uma lista de ferramentas e técnicas que as vagas costumam pedir
     (SQL, Power BI, Python, Spark, AWS...).
  2. As SUAS competências são as dessa lista que aparecem no arquivo do
     gerador de currículos (gerador-curriculos/base/competencias.yaml).
     Atualizou o currículo, a afinidade acompanha.
  3. Na vaga, procura quais itens da lista aparecem no título e na
     descrição. Afinidade = quantos desses você tem / quantos a vaga pede.

Vaga sem descrição (o Remotar não manda) ou que cita menos de 2 itens fica
sem %: seria um número sem base.
"""

import os
import re

from util import normalizar

COMPETENCIAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "gerador-curriculos", "base", "competencias.yaml")
MINIMO_DE_ITENS = 2

# nome mostrado -> padrão no texto já normalizado (minúsculo, sem acento).
ITENS = {
    "SQL": r"\bsql\b",
    "Python": r"\bpython\b",
    "R": r"(?:python|sql|excel)\W{1,3}(?:e |and |ou |or )?r\b(?!\$)|\blinguagem r\b|\br language\b|\bprogramacao em r\b",
    "Power BI": r"power ?bi",
    "DAX": r"\bdax\b",
    "Power Query": r"power ?query",
    "Excel": r"\bexcel\b",
    "VBA": r"\bvba\b|\bmacros?\b",
    "Google Sheets": r"google sheets|planilhas google",
    "Tableau": r"\btableau\b",
    "Looker": r"\blooker\b",
    "Qlik": r"\bqlik",
    "Metabase": r"\bmetabase\b",
    "ETL": r"\betl\b|\belt\b",
    "BigQuery": r"big ?query",
    "Oracle": r"\boracle\b",
    "pandas": r"\bpandas\b",
    "Selenium/Playwright": r"\bselenium\b|\bplaywright\b",
    "Matlab": r"\bmatlab\b",
    "Modelagem de dados": r"modelagem de dados|data modell?ing|modelo dimensional|dimensional model",
    "Dashboards": r"dashboards?|paineis",
    "KPIs": r"\bkpis?\b|indicadores",
    "Estatística": r"estatistic|statistic",
    "Pesquisa Operacional": r"pesquisa operacional|operations research|otimizacao|optimization",
    "Pricing": r"\bpricing\b|precificacao",
    "Supply Chain": r"supply chain|cadeia de suprimentos|abastecimento|estoque|inventory",
    "TOTVS": r"\btotvs\b|protheus",
    "SAP": r"\bsap\b",
    "Spark": r"\bspark\b|pyspark",
    "Databricks": r"databricks",
    "Snowflake": r"snowflake",
    "dbt": r"\bdbt\b",
    "Airflow": r"airflow",
    "AWS": r"\baws\b|amazon web services|redshift",
    "Azure": r"\bazure\b",
    "GCP": r"\bgcp\b|google cloud",
    "Machine Learning": r"machine learning|aprendizado de maquina|\bml\b",
    "Git": r"\bgit\b|github",
    "Salesforce": r"salesforce",
    "Alteryx": r"alteryx",
    "Scala/Java": r"\bscala\b|\bjava\b",
}
_COMPILADOS = {nome: re.compile(p) for nome, p in ITENS.items()}


def minhas_competencias(caminho=COMPETENCIAS):
  """Itens da lista que aparecem no seu arquivo de competências."""
  try:
    with open(caminho, "r", encoding="utf-8") as f:
      texto = normalizar(f.read())
  except FileNotFoundError:
    print(f"Arquivo de competências não encontrado: {caminho} (afinidade desligada)")
    return set()
  # "R" sozinho é ambíguo; no YAML ele aparece como item da lista ", R,".
  return {nome for nome, padrao in _COMPILADOS.items()
          if padrao.search(texto) or (nome == "R" and re.search(r",\s*r\s*,", texto))}


def itens_da_vaga(vaga):
  texto = normalizar(f"{vaga['titulo']} {vaga.get('descricao', '')}")
  return {nome for nome, padrao in _COMPILADOS.items() if padrao.search(texto)}


def calcular(vaga, minhas):
  """Devolve (porcentagem, itens que você tem, itens que faltam), ou None
  se a vaga não dá base pra calcular."""
  if not minhas or not vaga.get("descricao"):
    return None
  pedidos = itens_da_vaga(vaga)
  if len(pedidos) < MINIMO_DE_ITENS:
    return None
  tenho = pedidos & minhas
  return round(100 * len(tenho) / len(pedidos)), sorted(tenho), sorted(pedidos - minhas)


def completar(vagas, minhas):
  for vaga in vagas:
    vaga["afinidade"] = calcular(vaga, minhas)

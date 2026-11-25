"""Entrada preparada para o Databricks (Free Edition). PREPARADO, NÃO EXECUTADO.

Cole num notebook/job do Databricks com o repositório em um Repo. Lê o CSV de um
volume do Unity Catalog, usa as mesmas funções do pacote e grava a tabela horária.
Só deve ser citado como "rodado no Databricks" depois que alguém executar lá.
"""
from pyspark.sql import SparkSession

from src.pipeline import clean_and_aggregate

RAW_PATH = "/Volumes/main/default/wfm/nyc311_phone.csv"  # ajuste ao seu volume
OUT_TABLE = "main.default.wfm_hourly_calls"


def main() -> None:
    spark = SparkSession.builder.getOrCreate()
    raw = spark.read.option("header", True).csv(RAW_PATH)
    hourly, stats = clean_and_aggregate(raw)
    hourly.write.mode("overwrite").saveAsTable(OUT_TABLE)  # escrita nativa no Databricks
    print(stats)


if __name__ == "__main__":
    main()

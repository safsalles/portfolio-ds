"""Entrada para o Databricks. Executada no Databricks Free Edition (serverless) em 25/11/2026.

Só a etapa de pipeline roda lá: lê o CSV de um Volume, usa a mesma `clean_and_aggregate`
do pacote e grava uma tabela. Com o repositório numa Git folder, num notebook:

    import os, sys
    user = spark.sql("select current_user()").first()[0]
    sys.path.insert(0, f"/Workspace/Users/{user}/portfolio-ds/dimensionamento-equipe")
    from src import databricks_entry as job
    job.main()
"""
from pyspark.sql import SparkSession

from src.pipeline import clean_and_aggregate

RAW_PATH = "/Volumes/workspace/default/wfm/nyc311_phone.csv"  # ajuste ao seu volume
OUT_TABLE = "workspace.default.wfm_hourly_calls"


def main() -> None:
    spark = SparkSession.builder.getOrCreate()
    raw = spark.read.option("header", True).csv(RAW_PATH)
    hourly, stats = clean_and_aggregate(raw)
    hourly.write.mode("overwrite").saveAsTable(OUT_TABLE)  # escrita nativa no Databricks
    print(stats)


if __name__ == "__main__":
    main()

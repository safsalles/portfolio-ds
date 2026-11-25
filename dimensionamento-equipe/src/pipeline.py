"""Pipeline PySpark: limpa o NYC 311 e agrega chamadas de telefone por hora.

Só usa a API de DataFrame (sem RDD), para rodar igual no Databricks.
"""
from __future__ import annotations

import os
import sys

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

KEY, CREATED, CHANNEL = "unique_key", "created_date", "open_data_channel_type"


def build_spark(app_name: str = "wfm") -> SparkSession:
    # Workers Python usam o mesmo interpretador do driver (evita o `python` do PATH).
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    # Endereço fixo: hostnames com acento (ex.: "Maçã-PC") quebram o Spark local.
    return (
        SparkSession.builder.master("local[2]")
        .appName(app_name)
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def clean_and_aggregate(
    df: DataFrame, channel: str = "PHONE", tz: str = "America/New_York"
) -> tuple[DataFrame, dict]:
    """Devolve (hour_ts em UTC, calls) com horas vazias = 0, e contagens descartadas."""
    rows_in = df.count()
    ts = df.withColumn("_local", F.to_timestamp(F.col(CREATED)))
    with_ts = ts.filter(F.col("_local").isNotNull())
    null_ts = rows_in - with_ts.count()

    deduped = with_ts.dropDuplicates([KEY])
    duplicates = with_ts.count() - deduped.count()

    norm = F.upper(F.trim(F.col(CHANNEL)))
    phone = deduped.filter(norm == channel.upper())
    other_channel = deduped.count() - phone.count()

    hours = phone.select(
        F.date_trunc("hour", F.to_utc_timestamp(F.col("_local"), tz)).alias("hour_ts")
    )
    counts = hours.groupBy("hour_ts").agg(F.count(F.lit(1)).alias("calls"))

    bounds = counts.agg(F.min("hour_ts").alias("lo"), F.max("hour_ts").alias("hi"))
    grid = bounds.select(
        F.explode(F.sequence("lo", "hi", F.expr("interval 1 hour"))).alias("hour_ts")
    )
    full = (
        grid.join(counts, "hour_ts", "left")
        .withColumn("calls", F.coalesce(F.col("calls"), F.lit(0)).cast("long"))
        .orderBy("hour_ts")
    )
    stats = {
        "rows_in": rows_in,
        "null_ts": null_ts,
        "duplicates": duplicates,
        "other_channel": other_channel,
    }
    return full, stats


def run_pipeline(
    raw_path: str,
    out_path: str,
    start: str,
    end: str,
    spark: SparkSession | None = None,
    channel: str = "PHONE",
) -> dict:
    spark = spark or build_spark()
    raw = spark.read.option("header", True).csv(raw_path)
    local = F.to_timestamp(F.col(CREATED))
    raw = raw.filter(
        (local >= F.to_timestamp(F.lit(start))) | local.isNull()
    ).filter((local <= F.to_timestamp(F.lit(end))) | local.isNull())
    hourly, stats = clean_and_aggregate(raw, channel=channel)
    # Saída pequena (1 linha por hora): coleta e grava com pandas. Escrever Parquet
    # pelo Spark no Windows exige winutils.exe (binário externo); no Databricks use
    # hourly.write.parquet(...) direto.
    pdf = hourly.toPandas()
    pdf.to_parquet(out_path, index=False)
    stats["n_hours"] = int(len(pdf))
    stats["total_calls"] = int(pdf["calls"].sum())
    return stats


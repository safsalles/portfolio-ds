import pandas as pd

from src.pipeline import clean_and_aggregate, run_pipeline

COLS = ["unique_key", "created_date", "open_data_channel_type"]


def hourly(spark, rows, **kw):
    df = spark.createDataFrame(rows, COLS)
    out, stats = clean_and_aggregate(df, **kw)
    pdf = out.toPandas().sort_values("hour_ts").reset_index(drop=True)
    return pdf, stats


def test_counts_per_hour(spark):
    rows = [
        ("1", "2023-03-01 10:05:00", "PHONE"),
        ("2", "2023-03-01 10:30:00", "PHONE"),
        ("3", "2023-03-01 10:59:59", "PHONE"),
        ("4", "2023-03-01 11:00:00", "PHONE"),
    ]
    pdf, _ = hourly(spark, rows)
    assert list(pdf["calls"]) == [3, 1]


def test_filters_channel_case_and_spaces(spark):
    rows = [
        ("1", "2023-03-01 10:05:00", "PHONE"),
        ("2", "2023-03-01 10:06:00", " phone "),
        ("3", "2023-03-01 10:07:00", "ONLINE"),
    ]
    pdf, stats = hourly(spark, rows)
    assert pdf["calls"].sum() == 2
    assert stats["other_channel"] == 1


def test_drops_null_timestamp_and_duplicates(spark):
    rows = [
        ("1", "2023-03-01 10:05:00", "PHONE"),
        ("1", "2023-03-01 10:05:00", "PHONE"),
        ("2", None, "PHONE"),
        ("3", "2023-03-01 10:20:00", "PHONE"),
    ]
    pdf, stats = hourly(spark, rows)
    assert pdf["calls"].sum() == 2
    assert stats["null_ts"] == 1 and stats["duplicates"] == 1


def test_fills_missing_hours_with_zero(spark):
    rows = [
        ("1", "2023-03-01 10:05:00", "PHONE"),
        ("2", "2023-03-01 13:05:00", "PHONE"),
    ]
    pdf, _ = hourly(spark, rows)
    assert list(pdf["calls"]) == [1, 0, 0, 1]


def test_dst_keeps_every_row_and_no_duplicate_hours(spark):
    rows = [
        ("1", "2023-03-12 02:30:00", "PHONE"),
        ("2", "2023-03-12 03:10:00", "PHONE"),
        ("3", "2023-11-05 01:30:00", "PHONE"),
        ("4", "2023-11-05 01:45:00", "PHONE"),
        ("5", "2023-11-05 03:00:00", "PHONE"),
    ]
    pdf, _ = hourly(spark, rows)
    assert pdf["calls"].sum() == 5
    assert pdf["hour_ts"].is_unique


def test_run_pipeline_writes_parquet(spark, tmp_path):
    raw = tmp_path / "raw.csv"
    raw.write_text(
        "unique_key,created_date,open_data_channel_type\n"
        "1,2023-03-01 10:05:00,PHONE\n"
        "2,2023-03-01 10:06:00,PHONE\n"
        "3,2023-04-01 00:00:00,PHONE\n",
        encoding="utf-8",
    )
    out = tmp_path / "hourly.parquet"
    stats = run_pipeline(str(raw), str(out), "2023-03-01", "2023-03-31 23:59:59", spark=spark)
    saved = pd.read_parquet(out)
    assert stats["total_calls"] == 2 == saved["calls"].sum()
    assert len(saved) == stats["n_hours"]

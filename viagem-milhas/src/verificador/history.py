import csv
import os
from dataclasses import dataclass

FIELDS = ["date", "total_price_brl", "airlines", "layovers", "fare", "status"]


@dataclass(frozen=True)
class HistoryRecord:
    date: str
    total_price_brl: float | None
    airlines: str
    layovers: str
    fare: str | None
    status: str  # ok | error | empty


def _read_rows(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def upsert_record(path: str, record: HistoryRecord) -> None:
    rows = [r for r in _read_rows(path) if r["date"] != record.date]
    rows.append(
        {
            "date": record.date,
            "total_price_brl": "" if record.total_price_brl is None else str(float(record.total_price_brl)),
            "airlines": record.airlines,
            "layovers": record.layovers,
            "fare": record.fare or "",
            "status": record.status,
        }
    )
    rows.sort(key=lambda r: r["date"])
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def last_price(path: str, before_date: str) -> float | None:
    candidates = [
        r for r in _read_rows(path) if r["status"] == "ok" and r["date"] < before_date and r["total_price_brl"]
    ]
    if not candidates:
        return None
    return float(max(candidates, key=lambda r: r["date"])["total_price_brl"])


def has_ok_record(path: str, date: str) -> bool:
    return any(r["status"] == "ok" and r["date"] == date for r in _read_rows(path))


def latest_ok(path: str) -> HistoryRecord | None:
    ok_rows = [r for r in _read_rows(path) if r["status"] == "ok" and r["total_price_brl"]]
    if not ok_rows:
        return None
    r = max(ok_rows, key=lambda row: row["date"])
    return HistoryRecord(r["date"], float(r["total_price_brl"]), r["airlines"], r["layovers"], r["fare"] or None, r["status"])

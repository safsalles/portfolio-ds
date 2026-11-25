"""Baixa chamadas de TELEFONE do NYC 311 (NYC Open Data, API pública, sem conta).

Só 3 colunas e só o período pedido; paginação por chave (unique_key).
Uso: python scripts/download_311.py 2024-01-01 2025-12-31 data/raw/nyc311_phone.csv
"""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import requests

URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
COLS = ["unique_key", "created_date", "open_data_channel_type"]
PAGE = 50000


def download(start: str, end: str, out: Path) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    last, total = "", 0
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        while True:
            where = (
                f"open_data_channel_type='PHONE' AND created_date>='{start}T00:00:00' "
                f"AND created_date<='{end}T23:59:59' AND unique_key>'{last}'"
            )
            params = {"$select": ",".join(COLS), "$where": where, "$order": "unique_key", "$limit": PAGE}
            for attempt in range(5):
                try:
                    r = requests.get(URL, params=params, timeout=120)
                    r.raise_for_status()
                    break
                except requests.RequestException:
                    if attempt == 4:
                        raise
                    time.sleep(5 * (attempt + 1))
            rows = r.json()
            if not rows:
                return total
            for row in rows:
                w.writerow([row.get(c, "") for c in COLS])
            last = rows[-1]["unique_key"]
            total += len(rows)
            print(f"{total} linhas", flush=True)


if __name__ == "__main__":
    n = download(sys.argv[1], sys.argv[2], Path(sys.argv[3]))
    print(f"TOTAL {n}")

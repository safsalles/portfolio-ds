"""Prepara os dados do call center "Anonymous Bank" (Technion SEE Center, 1999).

Lê os 12 arquivos mensais (texto com 17 campos) e grava um extrato derivado e pequeno.
Fonte: documentação de Ilan Guedj e Avi Mandelbaum (2000). Ver data/exemplos/FONTES.md.

Uso: python scripts/preparar_technion.py data/raw/technion data/exemplos/technion_chamadas.csv.gz
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

import pandas as pd

COLS = ["date", "entry_s", "type", "outcome", "q_time_s", "ser_time_s"]
N_FIELDS = 17


def _hms(text: str) -> int:
    h, m, s = text.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def parse_technion(lines: Iterable[str]) -> pd.DataFrame:
    """Converte linhas do arquivo mensal. Separa por qualquer espaço em branco (algumas
    linhas usam espaços, não tabulação, entre prioridade e tipo). Linhas que não
    tiverem 17 campos válidos são descartadas e contadas em df.attrs['malformed']."""
    rows, malformed = [], 0
    for line in lines:
        if not line.strip() or line.startswith("vru+line"):
            continue
        f = line.split()
        if len(f) != N_FIELDS:
            malformed += 1
            continue
        try:
            rows.append((f[5], _hms(f[6]), f[4], f[12], int(f[11]), int(f[15])))
        except ValueError:
            malformed += 1
    df = pd.DataFrame(rows, columns=["date", "entry_s", "type", "outcome", "q_time_s", "ser_time_s"])
    df["date"] = pd.to_datetime("19" + df["date"], format="%Y%m%d", errors="coerce")
    bad = int(df["date"].isna().sum())
    df = df.dropna(subset=["date"]).reset_index(drop=True)
    df.attrs["malformed"] = malformed + bad
    return df[COLS]


def prepare(raw_dir: Path, out_path: Path) -> dict:
    files = sorted(Path(raw_dir).glob("*.txt"))
    parts, malformed = [], 0
    for f in files:
        part = parse_technion(f.read_text(encoding="utf-8", errors="replace").splitlines())
        malformed += part.attrs["malformed"]
        parts.append(part)
    df = pd.concat(parts, ignore_index=True).sort_values(["date", "entry_s"], kind="stable").reset_index(drop=True)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, compression="gzip")
    return {
        "files": len(files),
        "calls": int(len(df)),
        "served": int((df["outcome"] == "AGENT").sum()),
        "abandoned": int((df["outcome"] == "HANG").sum()),
        "phantom": int((df["outcome"] == "PHANTOM").sum()),
        "malformed": int(malformed),
        "period": [str(df["date"].min().date()), str(df["date"].max().date())],
    }


if __name__ == "__main__":
    print(prepare(Path(sys.argv[1]), Path(sys.argv[2])))

"""Onde ficam os dados e como os CSVs são lidos, com mensagens claras quando algo falta."""

import csv
from pathlib import Path

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "dados" / "brasileirao-2017"
DEFAULT_MIN_MINUTES = 850


class DataError(ValueError):
    """Os arquivos de dados não seguem o formato esperado."""


def read_csv(path):
    if not path.is_file():
        raise DataError(f"Arquivo não encontrado: {path}")
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def number(text, where):
    try:
        return float(text)
    except (TypeError, ValueError):
        raise DataError(f"Valor inválido em {where}: {text!r}") from None


def require_columns(found, required, filename):
    missing = [column for column in required if column not in found]
    if missing:
        raise DataError(f"Faltam colunas em {filename}: {', '.join(missing)}")

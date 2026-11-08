"""O problema de escolha: alternativas, critérios e a normalização das avaliações."""

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Problem:
    alternatives: tuple[str, ...]
    criteria: tuple[str, ...]
    values: np.ndarray  # alternativas x critérios, como vieram nos dados
    direction: np.ndarray  # 1 quando mais é melhor e 0 quando mais é pior
    weights: np.ndarray  # um peso por critério
    groups: np.ndarray | None = None  # grupo de cada alternativa, como o cargo
    complementarity: np.ndarray | None = None  # critérios x critérios; None = calcular dos dados


def normalize(values, direction, allow_constant=True, criteria=None):
    """Equação 3.1: põe cada critério entre 0 e 1, com 1 para a melhor avaliação.

    Em critérios de custo (direction 0), a escala é invertida. Um critério com o mesmo
    valor em todas as alternativas não diferencia ninguém: vira 0 quando `allow_constant`
    é verdadeiro, e dá erro quando é falso.
    """
    prepared = np.asarray(values, float)
    high, low = prepared.max(axis=0), prepared.min(axis=0)
    is_benefit = np.asarray(direction) >= 1
    best = np.where(is_benefit, high, low)
    worst = np.where(is_benefit, low, high)

    flat = best == worst
    if flat.any() and not allow_constant:
        names = list(criteria) if criteria is not None else list(range(len(flat)))
        raise ValueError(
            f"Critério com o mesmo valor em todas as alternativas: {names[int(np.flatnonzero(flat)[0])]}."
        )
    spread = np.where(flat, 1.0, best - worst)
    return (prepared - worst) / spread


def _read_rows(path, required):
    if not path.is_file():
        raise ValueError(f"Arquivo não encontrado: {path.name}")
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        found = reader.fieldnames or []
    missing = [column for column in required if column not in found]
    if missing:
        raise ValueError(f"Faltam colunas em {path.name}: {', '.join(missing)}")
    return rows, found


def load_problem(folder):
    """Lê criteria.csv, alternatives.csv e, se existir, complementarity.csv."""
    folder = Path(folder)
    criteria_rows, _ = _read_rows(folder / "criteria.csv", ["criterion", "direction", "weight"])
    criteria = tuple(row["criterion"].strip() for row in criteria_rows)
    direction = np.array([int(row["direction"]) for row in criteria_rows])
    weights = np.array([float(row["weight"]) for row in criteria_rows])

    rows, columns = _read_rows(folder / "alternatives.csv", ["alternative", *criteria])
    alternatives = tuple(row["alternative"].strip() for row in rows)
    values = np.array([[float(row[name]) for name in criteria] for row in rows])
    groups = np.array([row["group"].strip() for row in rows]) if "group" in columns else None

    complementarity = None
    path = folder / "complementarity.csv"
    if path.is_file():
        matrix_rows, _ = _read_rows(path, ["criterion", *criteria])
        by_name = {row["criterion"].strip(): row for row in matrix_rows}
        complementarity = np.zeros((len(criteria), len(criteria)))
        for i, first in enumerate(criteria):
            for j, second in enumerate(criteria):
                if i != j:
                    complementarity[i, j] = float(by_name[first][second])

    return Problem(alternatives, criteria, values, direction, weights, groups, complementarity)

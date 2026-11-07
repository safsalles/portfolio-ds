"""Os jogadores de linha: leitura dos dados (equivalente ao `impmem.m`) e a nota do time.

Cada par de critérios dá ao time um valor: o menor desempenho médio dos dois critérios,
multiplicado pelo peso médio e pela complementação do par. A nota é a fração de pares em
que o valor alcança o tau. Um critério forte não cobre um fraco, então um jogador vale
mais ou menos conforme o que os outros já cobrem. É a regra `minimo` do pacote `mem`, com
a posição no papel de grupo.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from comum.arquivos import (  # noqa: F401 (DataError e as constantes são usadas por quem importa daqui)
    DEFAULT_DATA_DIR,
    DEFAULT_MIN_MINUTES,
    DataError,
    number,
    read_csv,
    require_columns,
)
from comum.goleiros import rank_goalkeepers
from mem.pesos import complementarity_from_data, group_weights
from mem.problema import normalize
from mem.regras import minimum_rule

DEFAULT_TAU = 0.24


@dataclass(frozen=True)
class Dataset:
    players: list[str]  # nome com a sigla do clube, como "Hernanes (SAO)"
    positions: np.ndarray
    criteria: list[str]
    payment: np.ndarray  # jogadores x critérios, normalizado entre 0 e 1
    weights: np.ndarray
    complementarity: np.ndarray  # critérios x critérios
    goalkeeper: dict | None = None
    player_weights: np.ndarray | None = None  # jogadores x critérios
    clubs: np.ndarray | None = None  # sigla do clube de cada jogador
    minutes: np.ndarray | None = None


def _read_criteria(folder):
    columns, rows = read_csv(folder / "criteria.csv")
    require_columns(columns, ["criterion", "direction", "weight"], "criteria.csv")
    if not rows:
        raise DataError("criteria.csv não tem nenhum critério")

    names = [row["criterion"].strip() for row in rows]
    if len(set(names)) != len(names):
        raise DataError("criteria.csv tem critérios repetidos")

    direction = np.array([number(r["direction"], f"direction de {r['criterion']}") for r in rows])
    if not np.isin(direction, (0, 1)).all():
        raise DataError("Em criteria.csv, direction deve ser 1 (benefício) ou 0 (custo)")

    weights = np.array([number(r["weight"], f"weight de {r['criterion']}") for r in rows])
    return names, direction, weights


def _read_players(folder, criteria, min_minutes):
    columns, rows = read_csv(folder / "players.csv")
    require_columns(columns, ["player", "team", "position", "minutes", *criteria], "players.csv")
    rows = [row for row in rows if number(row["minutes"], row["player"]) >= min_minutes]
    if not rows:
        raise DataError(f"players.csv não tem jogadores com {min_minutes} minutos ou mais")

    totals = np.array(
        [[number(row[name], f"{row['player']} / {name}") for name in criteria] for row in rows]
    )
    minutes = np.array([float(row["minutes"]) for row in rows])
    values = totals / minutes[:, None] * 90
    return (
        [f"{row['player'].strip()} ({row['team'].strip()})" for row in rows],
        np.array([row["position"].strip().upper() for row in rows]),
        values,
        np.array([row["team"].strip() for row in rows]),
        minutes,
    )


def load_dataset(folder=DEFAULT_DATA_DIR, min_minutes=DEFAULT_MIN_MINUTES):
    folder = Path(folder)
    criteria, direction, weights = _read_criteria(folder)
    players, positions, values, clubs, minutes = _read_players(folder, criteria, min_minutes)
    goalkeepers = rank_goalkeepers(folder, min_minutes)
    return Dataset(
        players=players,
        positions=positions,
        criteria=criteria,
        # Um critério constante não diferencia ninguém e vira 0. No MATLAB, ele dividia por zero.
        payment=normalize(values, direction),
        weights=weights,
        complementarity=complementarity_from_data(values, positions),
        goalkeeper=goalkeepers[0] if goalkeepers else None,
        player_weights=group_weights(values, positions, direction),
        clubs=clubs,
        minutes=minutes,
    )


def build_scorer(dataset, tau=DEFAULT_TAU):
    """A regra do mínimo do método, com o desempenho ajustado pela posição de cada jogador."""
    payment = dataset.payment
    if dataset.player_weights is not None:
        payment = payment * dataset.player_weights
    return minimum_rule(payment, dataset.weights, dataset.complementarity, tau)

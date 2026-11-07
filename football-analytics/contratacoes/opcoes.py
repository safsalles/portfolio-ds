"""Os clubes, o time atual de cada um e as opções de contratação, da melhor para a pior.

Parte dos 10 jogadores de linha com mais minutos no clube, testa cada candidato no lugar
de cada titular da posição dele e ordena as trocas pela nota. Cada opção é uma
contratação só.
"""

import csv
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np

STARTERS = 10


@dataclass(frozen=True)
class Signing:
    rating: tuple[float, float]
    leaving: int
    arrival: int
    team: tuple[int, ...]


def _plain(text):
    """Tira acentos e maiúsculas, para aceitar `sao paulo` no lugar de `São Paulo`."""
    decomposed = unicodedata.normalize("NFKD", text.strip().casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def load_clubs(folder, dataset):
    """Devolve os clubes em ordem alfabética, como {sigla: nome}. O clubs.csv é opcional."""
    names = {}
    path = Path(folder) / "clubs.csv"
    if path.is_file():
        with path.open(encoding="utf-8-sig", newline="") as file:
            names = {row["code"].strip(): row["name"].strip() for row in csv.DictReader(file)}
    codes = {str(code): names.get(str(code), str(code)) for code in np.unique(dataset.clubs)}
    return dict(sorted(codes.items(), key=lambda item: _plain(item[1])))


def parse_club(text, clubs):
    """Aceita o número da lista, o nome ou a sigla do clube."""
    answer = _plain(text)
    if answer.isdigit() and 1 <= int(answer) <= len(clubs):
        return list(clubs)[int(answer) - 1]
    for code, name in clubs.items():
        if answer in (_plain(code), _plain(name)):
            return code
    raise ValueError(f"Não achei o clube {text.strip()!r}. Use o número, o nome ou a sigla.")


def starters(dataset, club, size=STARTERS):
    """Os jogadores com mais minutos no clube, com pelo menos um em cada posição.

    Só por minutos, o Vasco ficaria sem nenhum atacante, e não haveria quem substituir.
    """
    players = np.flatnonzero(dataset.clubs == club)
    ranking = [int(p) for p in players[np.argsort(-dataset.minutes[players], kind="stable")]]
    first_by_position = {}
    for player in ranking:
        first_by_position.setdefault(str(dataset.positions[player]), player)

    team = list(first_by_position.values())[:size]
    team += [player for player in ranking if player not in team][: size - len(team)]
    return sorted(team, key=ranking.index)


def candidates_for(dataset, club, position=None):
    """Jogadores de outros clubes, nas posições que têm titular para ser substituído."""
    outside = (dataset.clubs != club) & np.isin(
        dataset.positions, dataset.positions[starters(dataset, club)]
    )
    if position is not None:
        outside &= dataset.positions == position
    return [int(player) for player in np.flatnonzero(outside)]


def best_swap(scorer, dataset, team, arrival):
    """Coloca o contratado no lugar do titular da posição dele que mais melhora a nota."""
    options = []
    for leaving in team:
        if dataset.positions[leaving] == dataset.positions[arrival]:
            new_team = tuple(arrival if player == leaving else player for player in team)
            options.append(Signing(scorer.rate(new_team), leaving, arrival, new_team))
    return max(options, key=lambda signing: signing.rating)


def suggest(scorer, dataset, team, candidates):
    """Devolve a melhor troca de cada candidato, da melhor para a pior."""
    options = [best_swap(scorer, dataset, team, player) for player in candidates]
    return sorted(options, key=lambda signing: signing.rating, reverse=True)

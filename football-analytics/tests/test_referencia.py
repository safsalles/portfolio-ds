"""Confere que os resultados continuam iguais aos gravados antes da divisão.

O referencia.json foi gravado em 2026-11-07 com o código de antes da divisão entre
mem-ga/ e football-analytics/ (commit e206e9a do portfolio-ds). Se um destes testes falhar, algo mudou no
resultado. Não edite referencia.json:
ache a causa.
"""

import json
from pathlib import Path

import pytest

from comum.goleiros import rank_goalkeepers
from comum.jogadores import DEFAULT_DATA_DIR
from contratacoes.opcoes import candidates_for, load_clubs, starters, suggest
from escalacao.formacoes import PRESETS
from memga.busca import run_ga

REFERENCE = json.loads((Path(__file__).parent / "referencia.json").read_text(encoding="utf-8"))


@pytest.mark.slow
@pytest.mark.parametrize("formation", [*PRESETS, "livre"])
def test_time_igual_ao_gravado(dataset, scorer, formation):
    quotas = None if formation == "livre" else PRESETS[formation]
    result = run_ga(scorer, dataset.positions, quotas, 10, seed=REFERENCE["seed"])
    expected = REFERENCE["times"][formation]
    assert [dataset.players[p] for p in result.team] == expected["team"]
    assert result.score == expected["score"]


def test_goleiros_iguais_aos_gravados():
    assert [[k["name"], int(k["hits"])] for k in rank_goalkeepers()] == REFERENCE["goleiros"]


def test_contratacoes_iguais_as_gravadas(dataset, scorer):
    clubs = load_clubs(DEFAULT_DATA_DIR, dataset)
    assert sorted(clubs) == sorted(REFERENCE["contratacoes"])
    for club, expected in REFERENCE["contratacoes"].items():
        team = starters(dataset, club)
        assert [dataset.players[p] for p in team] == expected["starters"], club
        options = suggest(scorer, dataset, team, candidates_for(dataset, club))
        got = [
            [dataset.players[o.leaving], dataset.players[o.arrival], o.rating[0]]
            for o in options[: len(expected["opcoes"])]
        ]
        assert got == expected["opcoes"], club

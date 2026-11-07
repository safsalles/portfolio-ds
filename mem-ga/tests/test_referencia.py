"""Confere que o ranking do MEM continua igual ao gravado antes da divisão.

Se este teste falhar, algo mudou no resultado. Não edite referencia.json: ache a causa.
"""

import json
from pathlib import Path

import pytest

REFERENCE = json.loads((Path(__file__).parent / "referencia.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("choices", ["2", "3"])
def test_ranking_igual_ao_gravado(pequeno, choices):
    ranking = pequeno.rank(pequeno.load_problem(), int(choices), 0.24)
    got = [[c.position, list(c.alternatives), c.share] for c in ranking]
    assert got == REFERENCE[choices]

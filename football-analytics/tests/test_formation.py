import numpy as np
import pytest

from escalacao.formacoes import PRESETS, FormationError, parse_formation


@pytest.mark.parametrize("name", PRESETS)
def test_presets_work_with_the_real_data(dataset, name):
    assert sum(parse_formation(name, dataset.positions).values()) == 10


@pytest.mark.parametrize("text", ["", "  ", "livre", "LIVRE", "free"])
def test_free_team(dataset, text):
    assert parse_formation(text, dataset.positions) is None


def test_formation_can_be_typed_without_hyphens(dataset):
    assert parse_formation("4141", dataset.positions) == PRESETS["4-1-4-1"]


def test_three_at_the_back_has_no_full_backs():
    for name in ("3-5-2", "3-4-3", "3-6-1"):
        assert {"LE", "LD"}.isdisjoint(PRESETS[name])


def test_custom_formation_ignores_case_and_spaces(dataset):
    quotas = parse_formation("zag=3, LE=1,ld=1,vol=3,mei=1,ata=1", dataset.positions)
    assert quotas == {"ZAG": 3, "LE": 1, "LD": 1, "VOL": 3, "MEI": 1, "ATA": 1}


@pytest.mark.parametrize(
    "text, message",
    [
        ("9-9-9", "Não entendi"),
        ("999", "Não entendi"),
        ("zag=2", "soma 2"),
        ("zag=11", "soma 11"),
        ("zag=-1,ata=11", "Não entendi"),
        ("zag=5,zag=5", "duas vezes"),
        ("gol=1,zag=9", "dados têm 0"),
    ],
)
def test_invalid_formations(dataset, text, message):
    with pytest.raises(FormationError, match=message):
        parse_formation(text, dataset.positions)


def test_more_players_than_the_position_has():
    with pytest.raises(FormationError, match="dados têm 1"):
        parse_formation("A=2", np.array(["A", "B"]), team_size=2)

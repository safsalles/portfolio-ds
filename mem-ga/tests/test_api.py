"""Testa memga(), a função de entrada do pacote, com os exemplos que vêm dentro dele."""

import csv
from pathlib import Path

import pytest

from memga import GAConfig, load_example, memga, traditional_choice

REF = Path(__file__).resolve().parents[1] / "r" / "tests" / "testthat" / "ref"
QUOTAS = {"analyst": 2, "engineer": 1, "manager": 1}


def read_ref(name):
    with open(REF / name, newline="") as file:
        return list(csv.DictReader(file))


@pytest.fixture(scope="module")
def small():
    return load_example("small")


@pytest.fixture(scope="module")
def large():
    return load_example("large")


def test_examples_have_the_documented_shape(small, large):
    assert small.values.shape == (8, 6)
    assert small.direction[small.criteria.index("Absences")] == 0
    assert large.values.shape == (300, 8)
    assert sorted(set(large.groups.tolist())) == ["analyst", "engineer", "manager"]


def test_unknown_example_is_refused():
    with pytest.raises(ValueError, match="small"):
        load_example("huge")


@pytest.mark.parametrize("size", [2, 3])
def test_exhaustive_ranking_matches_the_gravado(small, size):
    """Mesmos conjuntos, posições e notas da regra `media` gravados antes (e no pacote R)."""
    ref = read_ref(f"exhaustive_media_{size}.csv")
    got = memga(small, size=size, tau=0.24).ranking
    assert [r.position for r in got] == [int(x["position"]) for x in ref]
    assert [", ".join(r.alternatives) for r in got] == [x["set"].replace(",", ", ") for x in ref]
    assert [r.score for r in got] == pytest.approx([float(x["score"]) for x in ref], abs=1e-12)


def test_pair_that_complements_beats_the_two_best(small):
    result = memga(small, size=2)
    assert result.score == pytest.approx(2 / 3)
    assert set(result.team) in ({"A1", "A3"}, {"A2", "A3"})
    assert set(result.traditional[0]) == {"A1", "A2"}
    assert result.traditional[1] < result.score
    assert "It ranks 3 in" in str(result)


def test_defaults_depend_on_the_method(small, large):
    assert memga(small, size=2).rule == "mean"
    result = memga(large, method="ga", quotas=QUOTAS, config=GAConfig(iterations=50), seed=1)
    assert result.rule == "minimum"


def test_ga_respects_quotas_and_the_seed(large):
    config = GAConfig(iterations=300)
    first = memga(large, method="ga", tau=0.54, quotas=QUOTAS, config=config, seed=3)
    again = memga(large, method="ga", tau=0.54, quotas=QUOTAS, config=config, seed=3)
    groups = sorted(large.groups[large.alternatives.index(name)] for name in first.team)
    assert groups == ["analyst", "analyst", "engineer", "manager"]
    assert first.team == again.team
    assert len(first.history) == 300
    assert first.history == sorted(first.history)


def test_ga_reaches_the_best_known_score_on_the_large_example(large):
    result = memga(large, method="ga", tau=0.54, quotas=QUOTAS, seed=1)
    assert result.score == pytest.approx(0.6785714285714286)
    assert set(result.team) == {"P007", "P038", "P192", "P276"}


def test_quotas_restrict_the_exhaustive_search(small):
    # sem grupos, as vagas não fazem sentido
    with pytest.raises(ValueError, match="groups"):
        memga(small, size=2, quotas={"a": 2})


def test_exhaustive_search_with_quotas_keeps_only_valid_sets(small):
    import numpy as np

    from memga.problema import Problem

    grouped = Problem(
        small.alternatives, small.criteria, small.values, small.direction, small.weights,
        np.array(["p", "p", "p", "q", "q", "q", "q", "q"]), small.complementarity,
    )
    result = memga(grouped, quotas={"p": 1, "q": 1}, tau=0.24)
    assert len(result.ranking) == 3 * 5
    for item in result.ranking:
        kinds = sorted(grouped.groups[grouped.alternatives.index(name)] for name in item.alternatives)
        assert kinds == ["p", "q"]


def test_traditional_choice_respects_quotas(large):
    result = memga(large, method="ga", quotas=QUOTAS, config=GAConfig(iterations=20), seed=1)
    groups = sorted(large.groups[large.alternatives.index(name)] for name in result.traditional[0])
    assert groups == ["analyst", "analyst", "engineer", "manager"]
    assert callable(traditional_choice)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({}, "size"),
        ({"size": 20}, "só 8"),
        ({"size": 2, "method": "grid"}, "Método"),
        ({"size": 2, "rule": "median"}, "Regra"),
        ({"size": 0}, "pelo menos 1"),
        ({"size": 2, "tau": 0}, "tau"),
    ],
)
def test_bad_arguments_stop_with_a_message(small, kwargs, message):
    with pytest.raises(ValueError, match=message):
        memga(small, **kwargs)


def test_size_must_match_quotas(large):
    with pytest.raises(ValueError, match="soma"):
        memga(large, size=3, quotas=QUOTAS, method="ga")
    with pytest.raises(ValueError, match="não estão"):
        memga(large, quotas={"pilot": 2}, method="ga")


def test_warns_when_no_set_reaches_tau():
    import numpy as np

    from memga.problema import Problem

    values = np.array([[9, 4, 3], [8, 5, 4], [3, 9, 8], [6, 6, 6]], float)
    tiny = Problem(("a", "b", "c", "d"), ("x", "y", "z"), values, np.array([1, 1, 0]), np.ones(3))
    with pytest.warns(UserWarning, match="Nenhum conjunto alcança o tau"):
        result = memga(tiny, size=2, tau=0.2)
    assert result.score == 0


def test_no_warning_when_some_set_reaches_tau(small, recwarn):
    memga(small, size=2)
    assert not [w for w in recwarn if "tau" in str(w.message)]


def test_radar_saves_a_png(small, tmp_path):
    target = tmp_path / "radar.png"
    memga(small, size=2).radar(path=target, show=False)
    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    other = tmp_path / "sem-comparacao.png"
    memga(small, size=2).radar(compare=False, path=other, show=False)
    assert other.exists()

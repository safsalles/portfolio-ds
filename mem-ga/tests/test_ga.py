from collections import Counter
from itertools import combinations

import numpy as np
import pytest

from mem_ga import PRESETS, GAConfig, TeamScorer, run_ga

SHORT = GAConfig(iterations=200, population=20, stagnation=5, mutation_attempts=3)


def strength_scorer(strengths):
    """Nota simples para os testes: todo time alcança o tau, e o desempate é a força."""
    payment = np.asarray(strengths, float).reshape(-1, 1)
    return TeamScorer(payment, np.ones((1, 1)), tau=0.0)


def test_same_seed_repeats_the_result(dataset, scorer):
    first = run_ga(scorer, dataset.positions, None, 10, SHORT, seed=7)
    second = run_ga(scorer, dataset.positions, None, 10, SHORT, seed=7)
    assert first == second


def test_free_team_has_no_repeated_player(dataset, scorer):
    result = run_ga(scorer, dataset.positions, None, 10, SHORT, seed=1)
    assert len(set(result.team)) == 10


@pytest.mark.parametrize("name", PRESETS)
def test_quotas_are_respected(dataset, scorer, name):
    quotas = PRESETS[name]
    result = run_ga(scorer, dataset.positions, quotas, 10, SHORT, seed=2)
    assert len(set(result.team)) == 10
    assert Counter(dataset.positions[list(result.team)].tolist()) == quotas


def test_position_with_zero_quota_stays_out(dataset, scorer):
    quotas = {"ZAG": 4, "VOL": 3, "ATA": 3, "MEI": 0}
    result = run_ga(scorer, dataset.positions, quotas, 10, SHORT, seed=3)
    assert "MEI" not in dataset.positions[list(result.team)]


def test_history_never_gets_worse_and_ends_at_the_score(dataset, scorer):
    result = run_ga(scorer, dataset.positions, None, 10, SHORT, seed=4)
    assert len(result.history) == SHORT.iterations
    assert all(a <= b for a, b in zip(result.history, result.history[1:]))
    assert result.history[-1] == result.score == scorer.rate(result.team)[0]


def test_progress_reports_without_changing_the_result(dataset, scorer):
    updates = []
    result = run_ga(scorer, dataset.positions, None, 10, SHORT, seed=4,
                    on_progress=lambda *update: updates.append(update))
    assert [update[0] for update in updates] == [100, 200]
    assert updates[-1] == (200, 200, result.score)
    assert result == run_ga(scorer, dataset.positions, None, 10, SHORT, seed=4)


def test_finishes_when_only_one_team_is_possible():
    positions = np.array(["A", "B", "C"])
    quotas = {"A": 1, "B": 1, "C": 1}
    config = GAConfig(iterations=30, population=5, stagnation=2, mutation_attempts=4)
    result = run_ga(strength_scorer([1, 2, 3]), positions, quotas, 3, config, seed=0)
    assert set(result.team) == {0, 1, 2}


def test_mutation_survives_running_out_of_players():
    positions = np.array(["A"] * 5)
    config = GAConfig(iterations=50, population=3, stagnation=1, mutation_attempts=100)
    result = run_ga(strength_scorer(range(5)), positions, None, 3, config, seed=0)
    assert set(result.team) == {2, 3, 4}


def test_finds_the_best_team_of_a_small_problem():
    rng = np.random.default_rng(0)
    payment = rng.random((14, 6))
    combos = np.array(list(combinations(range(6), 3)))
    matrix = np.zeros((6, len(combos)))
    matrix[combos.T, np.arange(len(combos))] = 1 / 3
    scorer = TeamScorer(payment, matrix, tau=0.6)

    best = max(scorer.rate(team) for team in combinations(range(14), 3))
    positions = np.array(["A"] * 14)
    config = GAConfig(iterations=1000, population=20)
    result = run_ga(scorer, positions, None, 3, config, seed=0)
    assert scorer.rate(result.team) == best


def test_complementary_team_beats_the_ten_strongest_players(dataset, scorer):
    strongest = np.argsort(-dataset.payment.sum(axis=1), kind="stable")[:10]
    result = run_ga(scorer, dataset.positions, None, 10, seed=0)
    assert result.score > scorer.rate(strongest)[0]


@pytest.mark.parametrize(
    "quotas, expected",
    [(None, 0.9039), (PRESETS["4-4-2"], 0.7942)],
    ids=["livre", "4-4-2"],
)
@pytest.mark.parametrize("seed", range(2))
def test_reaches_the_best_known_score(dataset, scorer, quotas, expected, seed):
    result = run_ga(scorer, dataset.positions, quotas, 10, seed=seed)
    assert result.score == pytest.approx(expected, abs=5e-5)

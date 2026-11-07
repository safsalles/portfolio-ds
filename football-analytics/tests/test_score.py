from itertools import combinations

import numpy as np
import pytest

from comum.jogadores import Dataset, build_scorer

def small_dataset(payment, weights=None, matrix_c=None):
    payment = np.asarray(payment, float)
    n_players, n_criteria = payment.shape
    return Dataset(
        players=[f"P{i}" for i in range(n_players)],
        positions=np.array(["A"] * n_players),
        criteria=[f"C{i}" for i in range(n_criteria)],
        payment=payment,
        weights=np.ones(n_criteria) if weights is None else weights,
        complementarity=np.ones((n_criteria, n_criteria)) if matrix_c is None else matrix_c,
    )


def pair_literal(payment, weights, matrix_c, team, tau):
    """Tradução direta da regra, em laços, para conferir a versão vetorizada."""
    means = payment[team].mean(axis=0)
    values = [
        min(means[j], means[k]) * (weights[j] + weights[k]) / 2 * matrix_c[j, k]
        for j, k in combinations(range(payment.shape[1]), 2)
    ]
    return np.mean(np.array(values) >= tau)


@pytest.mark.parametrize("seed", range(20))
def test_score_equals_the_literal_translation(seed):
    rng = np.random.default_rng(seed)
    n_criteria = int(rng.integers(4, 8))
    size = int(rng.integers(2, 8))
    weights = rng.random(n_criteria)
    matrix_c = rng.random((n_criteria, n_criteria))
    data = small_dataset(rng.random((12, n_criteria)), weights, matrix_c)
    team = rng.choice(12, size=size, replace=False).tolist()
    values = build_scorer(data).combo_values(team)
    # O pequeno deslocamento evita um tau exatamente igual a um valor do time.
    tau = float((values.min() + values.max()) / 2) + 1e-9

    score, _ = build_scorer(data, tau).rate(team)
    assert score == pytest.approx(pair_literal(data.payment, weights, matrix_c, team, tau))


def test_value_of_a_pair_by_hand():
    matrix_c = np.array([[0, 0.5], [0.5, 0]])
    scorer = build_scorer(small_dataset([[1, 0], [0, 1]], matrix_c=matrix_c), tau=0.2)
    assert scorer.combo_values([0, 1]) == pytest.approx([0.25])


def test_strong_criterion_does_not_cover_a_weak_one():
    data = small_dataset([[1, 0], [1, 0], [0, 1]])
    scorer = build_scorer(data, tau=0.4)
    assert scorer.rate([0, 1])[0] == 0
    assert scorer.rate([0, 2])[0] == 1


def test_only_the_weak_criterion_raises_the_value():
    data = small_dataset([[0.5, 1], [0, 0.5], [1, 0.5], [0, 1]])
    scorer = build_scorer(data, tau=1)
    base = scorer.combo_values([0, 1])
    assert scorer.combo_values([2, 1]) > base      # sobe o critério fraco
    assert scorer.combo_values([0, 3]) == base     # sobe só o critério forte


def test_same_player_adds_differently_to_different_teams():
    data = small_dataset([[1, 0], [0, 1], [1, 0], [0, 1]])
    scorer = build_scorer(data, tau=0.4)
    assert scorer.rate([0, 1])[0] > scorer.rate([0, 2])[0]


def test_tie_break_measures_what_is_missing_for_tau():
    data = small_dataset([[1, 0.2], [1, 0.2]])
    scorer = build_scorer(data, tau=0.1)
    assert scorer.rate([0, 1])[1] == pytest.approx(0.1)


def test_needs_two_criteria():
    with pytest.raises(ValueError, match="2 critérios"):
        build_scorer(small_dataset(np.ones((5, 1))))


def test_constant_criterion_never_passes_and_does_not_break():
    data = small_dataset([[0, 1, 1], [0, 1, 1]])
    assert build_scorer(data, tau=0.5).rate([0, 1])[0] == pytest.approx(1 / 3)


def test_a_higher_tau_is_harder_to_reach(dataset):
    team = np.argsort(-dataset.payment.sum(axis=1), kind="stable")[:10]
    scores = [build_scorer(dataset, tau).rate(team)[0] for tau in (0.15, 0.24, 0.35)]
    assert scores[0] > scores[1] > scores[2]


@pytest.mark.parametrize("tau", [0, -0.5, float("nan"), float("inf"), float("-inf")])
def test_tau_must_be_finite_and_positive(tau):
    with pytest.raises(ValueError, match="tau"):
        build_scorer(small_dataset(np.ones((5, 2))), tau=tau)

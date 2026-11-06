from itertools import combinations

import numpy as np
import pytest

from mem_ga import Dataset, build_scorer

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


def memc_literal(payment, weights, matrix_c, team, tau):
    """Tradução direta dos laços do `memc.m`, usada só para conferir a versão vetorizada."""
    hits = count = 0
    for combo in combinations(range(payment.shape[1]), len(team)):
        block = payment[np.ix_(team, combo)]
        pair_mean = np.mean([matrix_c[a, b] for a, b in combinations(combo, 2)])
        hits += block.mean() * weights[list(combo)].mean() * pair_mean >= tau
        count += 1
    return hits / count


@pytest.mark.parametrize("seed", range(20))
def test_score_equals_the_literal_translation(seed):
    rng = np.random.default_rng(seed)
    n_criteria = int(rng.integers(4, 8))
    size = int(rng.integers(2, n_criteria + 1))
    weights = rng.random(n_criteria)
    matrix_c = rng.random((n_criteria, n_criteria))
    data = small_dataset(rng.random((12, n_criteria)), weights, matrix_c)
    team = rng.choice(12, size=size, replace=False).tolist()
    values = build_scorer(data, size).combo_values(team)
    # O pequeno deslocamento evita um tau exatamente igual a um valor do time.
    tau = float((values.min() + values.max()) / 2) + 1e-9

    score, _ = build_scorer(data, size, tau).rate(team)
    assert score == pytest.approx(memc_literal(data.payment, weights, matrix_c, team, tau))


def test_a_player_is_worth_what_the_team_is_missing():
    # Os três jogadores têm a mesma força total. O jogador 2 cobre o buraco do jogador 0.
    data = small_dataset([[1, 1, 0], [1, 1, 0], [0, 1, 1]])
    scorer = build_scorer(data, 2, tau=0.7)
    twin, partner = scorer.rate([0, 1]), scorer.rate([0, 2])
    assert partner[0] > twin[0]
    assert partner[1] == pytest.approx(twin[1])


def test_a_higher_tau_is_harder_to_reach(dataset):
    team = np.argsort(-dataset.payment.sum(axis=1), kind="stable")[:10]
    scores = [build_scorer(dataset, 10, tau).rate(team)[0] for tau in (0.3, 0.54, 0.7)]
    assert scores[0] > scores[1] > scores[2]


def test_team_size_must_fit_the_criteria():
    with pytest.raises(ValueError, match="tamanho do time"):
        build_scorer(small_dataset(np.ones((5, 3))), 4)

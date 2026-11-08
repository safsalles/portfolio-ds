from itertools import combinations
from pathlib import Path

import numpy as np
import pytest

from mem.problema import Problem, load_problem, normalize
from mem.regras import MAX_MEAN_GROUPS, MeanRule, MinimumRule, build_rule, mean_rule, minimum_rule

DATA = Path(__file__).resolve().parents[1] / "exemplos" / "recrutamento-pequeno" / "data"


def literal_minimum(payment, weights, matrix_c, team, tau):
    """Tradução direta da regra do mínimo, em laços, para conferir a versão vetorizada."""
    means = payment[team].mean(axis=0)
    values = [
        min(means[j], means[k]) * (weights[j] + weights[k]) / 2 * matrix_c[j, k]
        for j, k in combinations(range(payment.shape[1]), 2)
    ]
    return np.mean(np.array(values) >= tau)


@pytest.mark.parametrize("seed", range(10))
def test_minimo_igual_a_traducao_literal(seed):
    rng = np.random.default_rng(seed)
    n_criteria = int(rng.integers(4, 8))
    payment, weights = rng.random((12, n_criteria)), rng.random(n_criteria)
    matrix_c = rng.random((n_criteria, n_criteria))
    team = rng.choice(12, size=int(rng.integers(2, 8)), replace=False).tolist()
    values = minimum_rule(payment, weights, matrix_c, 1.0).combo_values(team)
    tau = float((values.min() + values.max()) / 2) + 1e-9
    score, _ = minimum_rule(payment, weights, matrix_c, tau).rate(team)
    assert score == pytest.approx(literal_minimum(payment, weights, matrix_c, team, tau))


def test_no_minimo_criterio_forte_nao_cobre_o_fraco():
    rule = minimum_rule(np.array([[1.0, 0], [1, 0], [0, 1]]), np.ones(2), np.ones((2, 2)), 0.4)
    assert rule.rate([0, 1])[0] == 0
    assert rule.rate([0, 2])[0] == 1


def test_media_compensa_criterio_fraco_com_forte():
    payment = np.array([[1.0, 0], [1, 0], [0, 1]])
    rule = mean_rule(payment, np.ones(2), np.ones((2, 2)), 0.4, 2)
    # Pelo mínimo, [0, 1] não passa; pela média do par de critérios, passa.
    assert rule.rate([0, 1])[0] == 1


def test_as_duas_regras_devolvem_nota_e_desempate():
    payment = np.random.default_rng(0).random((6, 4))
    for rule in (
        minimum_rule(payment, np.ones(4), np.ones((4, 4)), 0.3),
        mean_rule(payment, np.ones(4), np.ones((4, 4)), 0.3, 3),
    ):
        score, tie_break = rule.rate([0, 1, 2])
        assert isinstance(score, float) and isinstance(tie_break, float)
        assert 0 <= score <= 1 and 0 <= tie_break <= 0.3


def test_desempate_da_media_e_o_quanto_falta_para_o_tau():
    payment = np.array([[1.0, 0.2], [1, 0.2]])
    rule = mean_rule(payment, np.ones(2), np.ones((2, 2)), 0.1, 2)
    # Um só grupo de critérios, com valor 0,6: passa do tau, então o desempate é o tau.
    assert rule.rate([0, 1]) == (1.0, pytest.approx(0.1))


def test_n_combos_conta_os_grupos_de_criterios():
    payment = np.ones((8, 6))
    assert minimum_rule(payment, np.ones(6), np.ones((6, 6)), 0.2).n_combos == 15
    assert mean_rule(payment, np.ones(6), np.ones((6, 6)), 0.2, 3).n_combos == 20


def test_media_acima_do_teto_da_erro_com_os_numeros():
    payment = np.ones((12, 18))
    with pytest.raises(ValueError, match=r"43758.*10000"):
        mean_rule(payment, np.ones(18), np.ones((18, 18)), 0.2, 10)
    assert MAX_MEAN_GROUPS == 10_000


@pytest.mark.parametrize("tau", [0, -0.5, float("nan"), float("inf")])
def test_tau_precisa_ser_finito_e_positivo(tau):
    with pytest.raises(ValueError, match="tau"):
        minimum_rule(np.ones((3, 2)), np.ones(2), np.ones((2, 2)), tau)
    with pytest.raises(ValueError, match="tau"):
        mean_rule(np.ones((3, 2)), np.ones(2), np.ones((2, 2)), tau, 2)


def test_precisa_de_dois_criterios():
    with pytest.raises(ValueError, match="2 critérios"):
        minimum_rule(np.ones((3, 1)), np.ones(1), np.ones((1, 1)), 0.2)


def test_build_rule_usa_a_complementacao_do_arquivo():
    problem = load_problem(DATA)
    rule = build_rule(problem, "media", 0.24, size=2)
    assert isinstance(rule, MeanRule)
    payment = normalize(problem.values, problem.direction)
    expected = mean_rule(payment, problem.weights, problem.complementarity, 0.24, 2)
    assert np.array_equal(rule.combo_values([0, 2]), expected.combo_values([0, 2]))


def test_build_rule_com_grupos_calcula_complementacao_e_pesos():
    rng = np.random.default_rng(1)
    values = rng.random((20, 4))
    groups = np.repeat(["a", "b"], 10)
    problem = Problem(
        tuple(map(str, range(20))), ("w", "x", "y", "z"), values, np.ones(4), np.ones(4), groups
    )
    rule = build_rule(problem, "minimo", 0.2)
    assert isinstance(rule, MinimumRule)
    assert not np.array_equal(rule.payment, values)


def test_build_rule_recusa_regra_desconhecida():
    with pytest.raises(ValueError, match="outra"):
        build_rule(load_problem(DATA), "outra", 0.24, size=2)


def test_build_rule_media_precisa_do_tamanho():
    with pytest.raises(ValueError, match="tamanho"):
        build_rule(load_problem(DATA), "media", 0.24)

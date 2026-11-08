import json
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest

from mem.busca import Choice, GAConfig, exhaustive, run_ga, traditional_choice
from mem.problema import load_problem
from mem.regras import build_rule, minimum_rule

DATA = Path(__file__).resolve().parents[1] / "exemplos" / "recrutamento-pequeno" / "data"
REFERENCE = json.loads((Path(__file__).parent / "referencia.json").read_text(encoding="utf-8"))
SHORT = GAConfig(iterations=200, population=20, stagnation=5, mutation_attempts=3)
QUOTAS = {"a": 2, "b": 1, "c": 1}


class SumRule:
    """Nota simples para os testes: todo conjunto alcança o tau, e o desempate é a força."""

    n_combos = 1

    def __init__(self, strengths):
        self.payment = np.asarray(strengths, float).reshape(-1, 1)

    def rate(self, team):
        return 1.0, float(self.payment[list(team)].sum())


@pytest.fixture(scope="module")
def grouped():
    rng = np.random.default_rng(3)
    payment = rng.random((40, 6))
    groups = np.repeat(["a", "b", "c"], [20, 12, 8])
    return minimum_rule(payment, np.ones(6), np.ones((6, 6)), 0.3), groups


def test_mesma_semente_repete_o_resultado(grouped):
    rule, groups = grouped
    assert run_ga(rule, groups, QUOTAS, 4, SHORT, seed=7) == run_ga(rule, groups, QUOTAS, 4, SHORT, seed=7)


def test_vagas_sao_respeitadas(grouped):
    rule, groups = grouped
    result = run_ga(rule, groups, QUOTAS, 4, SHORT, seed=2)
    assert len(set(result.team)) == 4
    assert Counter(groups[list(result.team)].tolist()) == QUOTAS


def test_sem_vagas_e_um_grupo_so(grouped):
    rule, groups = grouped
    result = run_ga(rule, groups, None, 5, SHORT, seed=1)
    assert len(set(result.team)) == 5


def test_grupo_com_zero_vagas_fica_de_fora(grouped):
    rule, groups = grouped
    result = run_ga(rule, groups, {"a": 3, "b": 1, "c": 0}, 4, SHORT, seed=3)
    assert "c" not in groups[list(result.team)]


def test_vaga_maior_que_o_grupo_da_erro_claro(grouped):
    rule, groups = grouped
    with pytest.raises(ValueError, match="O grupo c tem 8 alternativas, e foram pedidas 9."):
        run_ga(rule, groups, {"a": 1, "c": 9}, 10, SHORT, seed=0)


def test_conjunto_maior_que_as_alternativas_da_erro(grouped):
    rule, groups = grouped
    with pytest.raises(ValueError, match="alternativas"):
        run_ga(rule, groups, None, 41, SHORT, seed=0)


def test_historico_nunca_piora_e_termina_na_nota(grouped):
    rule, groups = grouped
    result = run_ga(rule, groups, None, 4, SHORT, seed=4)
    assert len(result.history) == SHORT.iterations
    assert all(a <= b for a, b in zip(result.history, result.history[1:]))
    assert result.history[-1] == result.score == rule.rate(result.team)[0]


def test_progresso_nao_muda_o_resultado(grouped):
    rule, groups = grouped
    updates = []
    result = run_ga(rule, groups, None, 4, SHORT, seed=4, on_progress=lambda *u: updates.append(u))
    assert [u[0] for u in updates] == [100, 200]
    assert result == run_ga(rule, groups, None, 4, SHORT, seed=4)


def test_termina_quando_so_um_conjunto_e_possivel():
    config = GAConfig(iterations=30, population=5, stagnation=2, mutation_attempts=4)
    result = run_ga(SumRule([1, 2, 3]), np.array(["A", "B", "C"]), {"A": 1, "B": 1, "C": 1}, 3, config, seed=0)
    assert set(result.team) == {0, 1, 2}


def test_mutacao_sobrevive_quando_acabam_as_alternativas():
    config = GAConfig(iterations=50, population=3, stagnation=1, mutation_attempts=100)
    result = run_ga(SumRule(range(5)), np.array(["A"] * 5), None, 3, config, seed=0)
    assert set(result.team) == {2, 3, 4}


def test_grupo_sem_reserva_nao_quebra():
    config = GAConfig(iterations=100, population=4, stagnation=2, climb_every=1)
    result = run_ga(SumRule(range(6)), np.array(["A", "A", "B", "B", "B", "B"]), {"A": 2, "B": 1}, 3, config, seed=0)
    assert {0, 1} <= set(result.team)


def test_acha_o_melhor_conjunto_com_a_regra_do_minimo():
    payment = np.random.default_rng(1).random((24, 6))
    rule = minimum_rule(payment, np.ones(6), np.ones((6, 6)), 0.62)
    best = max(rule.rate(team) for team in combinations(range(24), 4))
    assert 0 < best[0] < 1
    result = run_ga(rule, np.array(["A"] * 24), None, 4, GAConfig(iterations=1000, population=20), seed=0)
    assert rule.rate(result.team) == best


def trap_rule():
    """0-1-2 é o ótimo, mas trocar uma alternativa por vez a partir de 3-4-5 só piora."""
    class Trap:
        payment = np.zeros((16, 1))
        n_combos = 1

        def rate(self, team):
            team = set(team)
            if team == {0, 1, 2}:
                return 1.0, 0.0
            if team == {3, 4, 5}:
                return 0.5, 0.0
            return 0.1 * len(team & {3, 4, 5}), 0.0
    return Trap()


def test_mutacao_forte_escapa_do_otimo_local():
    config = GAConfig(iterations=3000, population=4, stagnation=2, climb_every=1)
    assert set(run_ga(trap_rule(), np.array(["A"] * 16), None, 3, config, seed=0).team) == {0, 1, 2}


@pytest.mark.parametrize("field", ["kick_size", "climb_every", "population"])
def test_configuracao_invalida(field):
    with pytest.raises(ValueError):
        GAConfig(**{field: 0})


@pytest.mark.parametrize("choices", ["2", "3"])
def test_exaustiva_com_a_media_reproduz_o_ranking_da_tese(choices):
    problem = load_problem(DATA)
    ranking = exhaustive(build_rule(problem, "media", 0.24, int(choices)), 8, int(choices))
    assert all(isinstance(choice, Choice) for choice in ranking)
    got = [[c.position, [problem.alternatives[i] for i in c.alternatives], c.score] for c in ranking]
    assert got == REFERENCE[choices]


def test_exaustiva_recusa_problema_grande_demais():
    payment = np.ones((60, 18))
    rule = minimum_rule(payment, np.ones(18), np.ones((18, 18)), 0.2)
    with pytest.raises(ValueError, match="avaliações"):
        exhaustive(rule, 60, 6)


def test_escolha_tradicional_sem_vagas_pega_as_mais_fortes():
    payment = np.array([[1.0], [5], [3], [4]])
    assert traditional_choice(payment, 2) == [1, 3]


def test_escolha_tradicional_com_vagas_pega_as_mais_fortes_de_cada_grupo():
    payment = np.array([[1.0], [5], [3], [4], [2]])
    groups = np.array(["a", "a", "b", "b", "b"])
    assert traditional_choice(payment, 3, groups, {"a": 1, "b": 2}) == [1, 3, 2]

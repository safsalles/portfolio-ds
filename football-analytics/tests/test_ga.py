from collections import Counter
from itertools import combinations

import numpy as np
import pytest

from comum.jogadores import Dataset, build_scorer
from escalacao.cli import main
from escalacao.formacoes import PRESETS
from memga.busca import GAConfig, run_ga

SHORT = GAConfig(iterations=200, population=20, stagnation=5, mutation_attempts=3)


@pytest.fixture(scope="module")
def free_team(dataset, scorer):
    """A rodada livre completa leva quase 40 s, então os testes a dividem."""
    return run_ga(scorer, dataset.positions, None, 10, seed=0)


class SumScorer:
    """Nota simples para os testes: todo time alcança o tau, e o desempate é a força."""

    def __init__(self, strengths):
        self.payment = np.asarray(strengths, float).reshape(-1, 1)

    def rate(self, team):
        return 1.0, float(self.payment[list(team)].sum())


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
    result = run_ga(SumScorer([1, 2, 3]), positions, quotas, 3, config, seed=0)
    assert set(result.team) == {0, 1, 2}


def test_mutation_survives_running_out_of_players():
    positions = np.array(["A"] * 5)
    config = GAConfig(iterations=50, population=3, stagnation=1, mutation_attempts=100)
    result = run_ga(SumScorer(range(5)), positions, None, 3, config, seed=0)
    assert set(result.team) == {2, 3, 4}


def test_finds_the_best_team_of_a_small_problem():
    rng = np.random.default_rng(0)
    payment = rng.random((14, 6))
    scorer = SumScorer(payment.sum(axis=1))

    best = max(scorer.rate(team) for team in combinations(range(14), 3))
    positions = np.array(["A"] * 14)
    config = GAConfig(iterations=1000, population=20)
    result = run_ga(scorer, positions, None, 3, config, seed=0)
    assert scorer.rate(result.team) == best


def test_finds_the_best_team_with_the_real_score():
    rng = np.random.default_rng(1)
    data = Dataset(
        players=[f"P{i}" for i in range(24)],
        positions=np.array(["A"] * 24),
        criteria=[f"C{i}" for i in range(6)],
        payment=rng.random((24, 6)),
        weights=np.ones(6),
        complementarity=np.ones((6, 6)),
    )
    scorer = build_scorer(data, tau=0.62)

    rates = [scorer.rate(team) for team in combinations(range(24), 4)]
    best = max(rates)
    # O problema só vale como teste se tiver platôs de nota zero e não saturar em 1.
    assert sum(score == 0 for score, _ in rates) > len(rates) / 2
    assert 0 < best[0] < 1

    config = GAConfig(iterations=1000, population=20)
    result = run_ga(scorer, data.positions, None, 4, config, seed=0)
    assert scorer.rate(result.team) == best


def test_complementary_team_beats_the_ten_strongest_players(scorer, free_team):
    def weakest_criterion(team):
        return scorer.payment[list(team)].mean(axis=0).min()

    strongest = np.argsort(-scorer.payment.sum(axis=1), kind="stable")[:10]
    # Alguns times sorteados já passam dos dez mais fortes, então só ganhar deles provaria pouco.
    assert free_team.score > scorer.rate(strongest)[0] + 0.2
    assert weakest_criterion(free_team.team) > weakest_criterion(strongest)


def trap_scorer():
    """Time 0-1-2 é o ótimo, mas trocar um jogador por vez a partir de 3-4-5 só piora."""
    class Trap:
        payment = np.zeros((16, 1))

        def rate(self, team):
            team = set(team)
            if team == {0, 1, 2}:
                return 1.0, 0.0
            if team == {3, 4, 5}:
                return 0.5, 0.0
            return 0.1 * len(team & {3, 4, 5}), 0.0
    return Trap()


def test_strong_mutation_escapes_a_local_optimum():
    config = GAConfig(iterations=3000, population=4, stagnation=2, climb_every=1)
    result = run_ga(trap_scorer(), np.array(["A"] * 16), None, 3, config, seed=0)
    assert set(result.team) == {0, 1, 2}


def test_without_strong_mutation_the_trap_holds():
    config = GAConfig(iterations=3000, population=4, stagnation=2, climb_every=10**9)
    result = run_ga(trap_scorer(), np.array(["A"] * 16), None, 3, config, seed=0)
    assert set(result.team) == {3, 4, 5}


def test_climb_keeps_the_formation(dataset, scorer):
    result = run_ga(scorer, dataset.positions, PRESETS["4-4-2"], 10, GAConfig(iterations=300), seed=0)
    assert Counter(dataset.positions[list(result.team)].tolist()) == Counter(PRESETS["4-4-2"])


def test_position_without_spare_players_does_not_break():
    positions = np.array(["A", "A", "B", "B", "B", "B"])
    config = GAConfig(iterations=100, population=4, stagnation=2, climb_every=1)
    result = run_ga(SumScorer(range(6)), positions, {"A": 2, "B": 1}, 3, config, seed=0)
    assert {0, 1} <= set(result.team)


def test_impossible_tau_still_finishes(dataset):
    result = run_ga(build_scorer(dataset, 5.0), dataset.positions, None, 10, GAConfig(iterations=200), seed=0)
    assert result.score == 0


@pytest.mark.parametrize("field", ["kick_size", "climb_every"])
def test_invalid_kick_settings(field):
    with pytest.raises(ValueError):
        GAConfig(**{field: 0})


def test_free_team_reaches_the_best_known_score(free_team):
    assert free_team.score == pytest.approx(0.9739, abs=5e-5)


@pytest.mark.parametrize(
    "quotas, expected, seed",
    [(None, 0.9739, 1), (PRESETS["4-4-2"], 0.9608, 0), (PRESETS["4-4-2"], 0.9608, 1)],
    ids=["livre", "4-4-2 semente 0", "4-4-2 semente 1"],
)
def test_reaches_the_best_known_score(dataset, scorer, quotas, expected, seed):
    result = run_ga(scorer, dataset.positions, quotas, 10, seed=seed)
    assert result.score == pytest.approx(expected, abs=5e-5)


@pytest.mark.parametrize("size", ["0", "-1", "1000"])
def test_invalid_team_size_stops_with_a_message(size, capsys):
    with pytest.raises(SystemExit) as stop:
        main(["--seed", "1", "--iterations", "5", "--formation", "livre", "--team-size", size])
    assert str(stop.value).startswith("Erro:")
    assert "jogador" in str(stop.value)
    assert "Traceback" not in capsys.readouterr().err


def test_team_size_larger_than_the_players_is_rejected_by_the_search(dataset):
    with pytest.raises(ValueError, match="alternativas"):
        run_ga(build_scorer(dataset), dataset.positions, None, len(dataset.players) + 1, SHORT, seed=0)


@pytest.mark.parametrize("tau", ["0", "-1", "nan", "inf", "-inf"])
def test_invalid_tau_is_rejected_on_the_command_line(tau, capsys):
    with pytest.raises(SystemExit) as stop:
        main(["--formation", "4-4-2", "--tau", tau])
    assert stop.value.code == 2
    assert "tau" in capsys.readouterr().err

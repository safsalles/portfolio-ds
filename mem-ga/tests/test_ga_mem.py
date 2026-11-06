from itertools import combinations

import numpy as np
import pytest

from ga_mem import (
    SigningSearch,
    candidates_for,
    load_clubs,
    main,
    parse_club,
    parse_position,
    parse_signings,
    starters,
    suggest,
)
from mem_ga import DEFAULT_DATA_DIR, GAConfig, TeamScorer, build_scorer

FAST = ["--seed", "1", "--iterations", "100", "--population", "10"]


@pytest.fixture(scope="module")
def clubs(dataset):
    return load_clubs(DEFAULT_DATA_DIR, dataset)


@pytest.fixture(scope="module")
def low_tau_scorer(dataset):
    return build_scorer(dataset, 10, 0.36)


def test_clubs_are_listed_in_alphabetical_order(clubs):
    names = list(clubs.values())
    assert len(names) == 20
    assert names[:2] == ["Atlético GO", "Atlético MG"]
    assert names[-1] == "Vitória"


@pytest.mark.parametrize("text", ["16", "Santos", "santos", " SANTOS ", "SAN", "san"])
def test_club_by_number_name_or_code(clubs, text):
    assert parse_club(text, clubs) == "SAN"


@pytest.mark.parametrize("text", ["São Paulo", "sao paulo", "SAO"])
def test_club_name_ignores_accents(clubs, text):
    assert parse_club(text, clubs) == "SAO"


@pytest.mark.parametrize("text", ["0", "21", "Real Madrid", ""])
def test_unknown_club(clubs, text):
    with pytest.raises(ValueError, match="Não achei"):
        parse_club(text, clubs)


def test_starters_are_the_ten_with_more_minutes(dataset):
    team = starters(dataset, "SAN")
    others = np.flatnonzero(dataset.clubs == "SAN")
    bench = [player for player in others if player not in team]
    assert len(team) == 10
    assert set(dataset.clubs[team]) == {"SAN"}
    assert dataset.minutes[team].min() >= dataset.minutes[bench].max()


def test_candidates_come_from_other_clubs(dataset):
    candidates = candidates_for(dataset, "SAN", "ZAG")
    assert "SAN" not in set(dataset.clubs[candidates])
    assert set(dataset.positions[candidates]) == {"ZAG"}


def test_signing_replaces_a_starter_of_the_same_position(dataset, low_tau_scorer):
    team = starters(dataset, "SAN")
    options = suggest(low_tau_scorer, dataset, team, candidates_for(dataset, "SAN"))
    for option in options[:20]:
        (leaving, arrival), = option.swaps
        assert leaving in team
        if dataset.positions[arrival] in dataset.positions[team]:
            assert dataset.positions[leaving] == dataset.positions[arrival]


def test_any_starter_can_leave_when_the_position_is_missing():
    class Data:
        positions = np.array(["A", "A", "B"])

    scorer = TeamScorer(np.array([[1.0], [5.0], [9.0]]), np.ones((1, 1)), 0.0)
    signing = SigningSearch(scorer, Data, [0, 1]).evaluate((2,))
    assert signing.swaps == ((0, 2),)


def test_one_signing_finds_the_best_of_all_candidates(dataset, low_tau_scorer):
    team = starters(dataset, "VAS")
    candidates = candidates_for(dataset, "VAS", "MEI")
    best = suggest(low_tau_scorer, dataset, team, candidates)[0]

    expected = max(
        low_tau_scorer.rate([arrival if p == leaving else p for p in team])
        for arrival in candidates
        for leaving in team
        if dataset.positions[leaving] == "MEI"
    )
    assert best.rating == expected


def test_results_are_sorted_from_best_to_worst(dataset, low_tau_scorer):
    options = suggest(low_tau_scorer, dataset, starters(dataset, "COR"), candidates_for(dataset, "COR"))
    ratings = [option.rating for option in options]
    assert ratings == sorted(ratings, reverse=True)
    assert len(ratings) == len(candidates_for(dataset, "COR"))


def test_package_respects_the_rules(dataset, low_tau_scorer):
    team = starters(dataset, "GRE")
    candidates = candidates_for(dataset, "GRE", "ZAG")
    config = GAConfig(iterations=300, population=20)
    best = suggest(low_tau_scorer, dataset, team, candidates, 2, config, seed=1)[0]

    assert len(best.swaps) == 2
    assert len(set(best.team)) == 10
    assert {arrival for _, arrival in best.swaps} <= set(candidates)
    assert len({leaving for leaving, _ in best.swaps}) == 2


def test_same_seed_repeats_a_package(dataset, low_tau_scorer):
    team = starters(dataset, "FLA")
    candidates = candidates_for(dataset, "FLA")
    config = GAConfig(iterations=200, population=20)
    first = suggest(low_tau_scorer, dataset, team, candidates, 2, config, seed=5)[0]
    second = suggest(low_tau_scorer, dataset, team, candidates, 2, config, seed=5)[0]
    assert first == second


def test_genetic_search_finds_the_best_pair_of_a_small_problem(dataset, low_tau_scorer):
    team = starters(dataset, "COR")
    candidates = candidates_for(dataset, "COR", "LE")[:12]
    search = SigningSearch(low_tau_scorer, dataset, team)
    expected = max(search.rate(pair) for pair in combinations(candidates, 2))

    config = GAConfig(iterations=500, population=20)
    best = suggest(low_tau_scorer, dataset, team, candidates, 2, config, seed=0)[0]
    assert best.rating == expected


@pytest.mark.parametrize("text", ["qualquer", "Qualquer", "any"])
def test_any_position(text):
    assert parse_position(text, ["ATA", "ZAG"]) is None


def test_position_ignores_case():
    assert parse_position("zag", ["ATA", "ZAG"]) == "ZAG"


def test_unknown_position():
    with pytest.raises(ValueError, match="Não achei a posição"):
        parse_position("GOL", ["ATA", "ZAG"])


def test_blank_signings_means_one():
    assert parse_signings("", 10) == 1


@pytest.mark.parametrize("text", ["0", "11", "dois"])
def test_invalid_signings(text):
    with pytest.raises(ValueError, match="1 a 10"):
        parse_signings(text, 10)


def test_questions_flow_with_a_chosen_position(monkeypatch, capsys):
    answers = iter(["Marte", "16", "3", "1", "gol", "zag", "1"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    main(FAST)
    output = capsys.readouterr().out
    assert "16. Santos (SAN)" in output
    assert "Não achei o clube" in output
    assert "Responda 1 ou 2" in output
    assert "Não achei a posição" in output
    assert "Santos: nota atual" in output
    assert "Melhores opções:" in output


def test_questions_flow_with_any_position(monkeypatch, capsys):
    answers = iter(["vasco", "2", ""])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    main(FAST)
    assert "Vasco: nota atual" in capsys.readouterr().out


def test_flags_skip_the_questions(monkeypatch, capsys):
    def fail(prompt):
        raise AssertionError("não deveria perguntar")

    monkeypatch.setattr("builtins.input", fail)
    main([*FAST, "--club", "COR", "--position", "qualquer", "--signings", "2"])
    output = capsys.readouterr().out
    assert "Corinthians: nota atual" in output
    assert "iteração 100/100" in output
    assert output.count("  Sai ") == 2


def test_pitch_shows_the_goalkeeper_of_the_club(capsys):
    main([*FAST, "--club", "SAN", "--position", "ATA", "--signings", "1"])
    assert "Vanderlei (SAN)" in capsys.readouterr().out


def test_invalid_club_flag_stops_with_a_message():
    with pytest.raises(SystemExit, match="Erro"):
        main([*FAST, "--club", "Marte"])

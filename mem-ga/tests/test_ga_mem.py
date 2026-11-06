import numpy as np
import pytest

from ga_mem import (
    candidates_for,
    load_clubs,
    main,
    parse_club,
    parse_options,
    parse_position,
    starters,
    suggest,
)
from mem_ga import DEFAULT_DATA_DIR


@pytest.fixture(scope="module")
def clubs(dataset):
    return load_clubs(DEFAULT_DATA_DIR, dataset)


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


def test_starters_have_every_position_and_then_the_most_minutes(dataset):
    for club in np.unique(dataset.clubs):
        team = starters(dataset, club)
        squad = np.flatnonzero(dataset.clubs == club)
        assert len(team) == 10
        assert set(dataset.clubs[team]) == {club}
        assert set(dataset.positions[team]) == set(dataset.positions[squad])


def test_vasco_has_an_attacker_even_without_one_among_the_most_used(dataset):
    squad = np.flatnonzero(dataset.clubs == "VAS")
    most_used = squad[np.argsort(-dataset.minutes[squad], kind="stable")][:10]
    assert "ATA" not in dataset.positions[most_used]
    assert "ATA" in dataset.positions[starters(dataset, "VAS")]


def test_candidates_come_from_other_clubs(dataset):
    candidates = candidates_for(dataset, "SAN", "ZAG")
    assert "SAN" not in set(dataset.clubs[candidates])
    assert set(dataset.positions[candidates]) == {"ZAG"}


def test_signing_replaces_a_starter_of_the_same_position(dataset, scorer):
    team = starters(dataset, "SAN")
    for option in suggest(scorer, dataset, team, candidates_for(dataset, "SAN")):
        assert option.leaving in team
        assert dataset.positions[option.leaving] == dataset.positions[option.arrival]


def test_candidates_need_a_starter_in_their_position():
    class Data:
        clubs = np.array(["X", "X", "Y", "Y"])
        positions = np.array(["A", "A", "A", "B"])
        minutes = np.array([900, 900, 900, 900])

    assert candidates_for(Data, "X") == [2]


def test_attackers_only_replace_attackers(dataset, scorer):
    team = starters(dataset, "VAS")
    options = suggest(scorer, dataset, team, candidates_for(dataset, "VAS", "ATA"))
    assert {str(dataset.positions[option.leaving]) for option in options} == {"ATA"}


def test_each_option_changes_one_player_and_keeps_the_others(dataset, scorer):
    team = starters(dataset, "VAS")
    for option in suggest(scorer, dataset, team, candidates_for(dataset, "VAS"))[:20]:
        assert set(option.team) == (set(team) - {option.leaving}) | {option.arrival}


def test_asking_for_five_attackers_lists_five_options_for_one_slot(capsys):
    main(["--club", "VAS", "--position", "ATA", "--options", "5"])
    output = capsys.readouterr().out
    assert output.count("  Sai ") == 1
    listed = output.split("Melhores opções:")[1].strip().splitlines()
    assert len(listed) == 5
    assert all("no lugar de Andrés Ríos" in line for line in listed)


def test_one_signing_finds_the_best_of_all_candidates(dataset, scorer):
    team = starters(dataset, "VAS")
    candidates = candidates_for(dataset, "VAS", "MEI")
    best = suggest(scorer, dataset, team, candidates)[0]

    expected = max(
        scorer.rate([arrival if p == leaving else p for p in team])
        for arrival in candidates
        for leaving in team
        if dataset.positions[leaving] == "MEI"
    )
    assert best.rating == expected


def test_results_are_sorted_from_best_to_worst(dataset, scorer):
    options = suggest(scorer, dataset, starters(dataset, "COR"), candidates_for(dataset, "COR"))
    ratings = [option.rating for option in options]
    assert ratings == sorted(ratings, reverse=True)
    assert len(ratings) == len(candidates_for(dataset, "COR"))


@pytest.mark.parametrize("text", ["qualquer", "Qualquer", "any"])
def test_any_position(text):
    assert parse_position(text, ["ATA", "ZAG"]) is None


def test_position_ignores_case():
    assert parse_position("zag", ["ATA", "ZAG"]) == "ZAG"


def test_unknown_position():
    with pytest.raises(ValueError, match="Não achei a posição"):
        parse_position("GOL", ["ATA", "ZAG"])


def test_blank_options_means_five():
    assert parse_options("", 40) == 5


def test_blank_options_respects_a_short_list():
    assert parse_options("", 3) == 3


@pytest.mark.parametrize("text", ["0", "11", "dois"])
def test_invalid_options(text):
    with pytest.raises(ValueError, match="1 a 10"):
        parse_options(text, 10)


def test_questions_flow_with_a_chosen_position(monkeypatch, capsys):
    answers = iter(["Marte", "16", "3", "1", "gol", "zag", "3"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    main([])
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
    main([])
    assert "Vasco: nota atual" in capsys.readouterr().out


def test_flags_skip_the_questions(monkeypatch, capsys):
    def fail(prompt):
        raise AssertionError("não deveria perguntar")

    monkeypatch.setattr("builtins.input", fail)
    main(["--club", "COR", "--position", "qualquer", "--options", "2"])
    output = capsys.readouterr().out
    assert "Corinthians: nota atual" in output
    assert len(output.split("Melhores opções:")[1].strip().splitlines()) == 2


def test_pitch_shows_the_goalkeeper_of_the_club(capsys):
    main(["--club", "SAN", "--position", "ATA", "--options", "1"])
    assert "Vanderlei (SAN)" in capsys.readouterr().out


def test_invalid_club_flag_stops_with_a_message():
    with pytest.raises(SystemExit, match="Erro"):
        main(["--club", "Marte"])


def test_club_without_candidates_stops_with_a_message(capsys):
    with pytest.raises(SystemExit) as stop:
        main(["--club", "PON", "--position", "qualquer", "--options", "3", "--min-minutes", "3100"])
    assert str(stop.value).startswith("Erro:")
    assert "candidato" in str(stop.value)
    assert "1 a 0" not in capsys.readouterr().out


def test_club_without_candidates_does_not_ask_for_the_amount(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("não deveria perguntar"))
    with pytest.raises(SystemExit, match="candidato"):
        main(["--club", "PON", "--position", "qualquer", "--min-minutes", "3100"])


def test_short_squad_shows_how_many_players_were_used(capsys):
    main(["--club", "CHA", "--position", "qualquer", "--options", "1", "--min-minutes", "1400"])
    output = capsys.readouterr().out
    assert "Aviso" in output
    assert "9 jogadores" in output
    assert "Chapecoense: nota atual" in output


def test_full_squad_has_no_warning(capsys):
    main(["--club", "COR", "--position", "qualquer", "--options", "1"])
    assert "Aviso" not in capsys.readouterr().out


@pytest.mark.parametrize("tau", ["0", "-1", "nan", "inf"])
def test_invalid_tau_is_rejected_on_the_command_line(tau, capsys):
    with pytest.raises(SystemExit) as stop:
        main(["--club", "COR", "--tau", tau])
    assert stop.value.code == 2
    assert "tau" in capsys.readouterr().err

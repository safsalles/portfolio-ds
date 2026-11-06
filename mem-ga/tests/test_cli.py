import numpy as np
import pytest

from mem_ga import main, pitch_lines

FAST = ["--seed", "1", "--iterations", "50", "--population", "10"]


def write_small_dataset(folder):
    (folder / "criteria.csv").write_text(
        "criterion,direction,weight,cut\nspeed,1,1,\nerrors,0,2,\nrating,1,1,5\n",
        encoding="utf-8",
    )
    (folder / "players.csv").write_text(
        "player,team,position,minutes,speed,errors,rating\n"
        "Ana,X,A,900,9,1,7\nBia,X,A,900,5,3,4\nCaio,Y,B,900,7,2,6\nDani,Y,B,900,3,4,2\n",
        encoding="utf-8",
    )


def test_asks_for_the_formation_until_it_is_valid(monkeypatch, capsys):
    answers = iter(["9-9-9", "4-3-3"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    main(FAST)
    output = capsys.readouterr().out
    assert "Não entendi" in output
    assert "Nota do time" in output


def test_blank_answer_means_free_team(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    main(FAST)
    assert "Nota do time" in capsys.readouterr().out


def test_formation_flag_skips_the_question(monkeypatch, capsys):
    def fail(prompt):
        raise AssertionError("não deveria perguntar")

    monkeypatch.setattr("builtins.input", fail)
    main([*FAST, "--formation", "4-4-2"])
    assert "Nota do time" in capsys.readouterr().out


def test_tau_flag_is_used(capsys):
    main([*FAST, "--formation", "4-4-2", "--tau", "0.1"])
    assert "Nota do time: 1.0000 (tau 0.1" in capsys.readouterr().out


def test_invalid_flag_stops_with_a_message():
    with pytest.raises(SystemExit, match="Erro"):
        main([*FAST, "--formation", "zag=2"])


def test_runs_with_another_dataset(tmp_path, capsys):
    write_small_dataset(tmp_path)
    main([*FAST, "--data", str(tmp_path), "--team-size", "2", "--formation", "A=1,B=1"])
    output = capsys.readouterr().out
    assert "Ana" in output or "Bia" in output
    assert "[     ]" not in output


def test_output_explains_the_number_next_to_each_player(capsys):
    main([*FAST, "--formation", "4-4-2"])
    output = capsys.readouterr().out
    assert "Critérios atingidos" in output
    assert " de 18" in output


def test_progress_is_shown_while_it_runs(capsys):
    main([*FAST, "--formation", "4-4-2"])
    output = capsys.readouterr().out
    assert "iteração 50/50" in output
    assert "melhor nota" in output


def test_pitch_goes_from_attack_to_defense(dataset, find):
    team = find(["Luan (GRE)", "Keno (PAL)", "Fagner (COR)", "Fábio (CAM)", "Gustavo Scarpa (FLU)",
                 "Hernanes (SAO)", "Juninho (BAH)", "Michel (GRE)", "Fabián Balbuena (COR)", "Réver (FLA)"])
    text = "\n".join(pitch_lines(dataset, dataset.payment.sum(axis=1), team))
    assert text.index("Keno (PAL)") < text.index("Hernanes (SAO)") < text.index("Michel (GRE)") < text.index("Réver (FLA)")

    defense = next(line for line in text.splitlines() if "Réver (FLA)" in line)
    assert defense.index("Fábio (CAM)") < defense.index("Réver (FLA)") < defense.index("Fagner (COR)")


def test_goalkeeper_appears_on_the_pitch_and_in_the_list(capsys):
    main([*FAST, "--formation", "4-4-2"])
    output = capsys.readouterr().out
    assert "Goleiro: Cássio (COR)" in output
    assert output.count("Cássio (COR)") == 2


def test_pitch_lines_have_the_same_width_and_show_everyone(dataset):
    strengths = dataset.payment.sum(axis=1)
    team = np.argsort(-strengths, kind="stable")[:10].tolist()
    lines = pitch_lines(dataset, strengths, team)
    assert len({len(line) for line in lines}) == 1
    assert all(dataset.players[player] in "\n".join(lines) for player in team)

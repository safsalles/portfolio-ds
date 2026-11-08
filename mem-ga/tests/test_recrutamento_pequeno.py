from itertools import combinations
from math import comb

import numpy as np
import pytest

from mem.busca import MAX_EVALUATIONS
from mem.problema import Problem, normalize
from mem.regras import mean_rule


def problem(payment, direction=None, weights=None, complementarity=None):
    payment = np.array(payment, float)
    n_alternatives, n_criteria = payment.shape
    if complementarity is None:
        complementarity = np.ones((n_criteria, n_criteria)) - np.eye(n_criteria)
    return Problem(
        alternatives=tuple(f"A{i + 1}" for i in range(n_alternatives)),
        criteria=tuple(f"C{j + 1}" for j in range(n_criteria)),
        values=payment,
        direction=np.ones(n_criteria, int) if direction is None else np.array(direction),
        weights=np.ones(n_criteria) if weights is None else np.array(weights, float),
        complementarity=np.array(complementarity, float),
    )


def norm(data):
    return normalize(data.values, data.direction, allow_constant=False, criteria=data.criteria)


def rule_of(data, choices, tau=1.0):
    return mean_rule(norm(data), data.weights, data.complementarity, tau, choices)


SMALL = problem(
    [[10, 0, 4], [0, 10, 8], [5, 5, 0], [10, 10, 10]],
    weights=[1.0, 0.5, 0.8],
    complementarity=[[0, 0.2, 0.6], [0.2, 0, 0.9], [0.6, 0.9, 0]],
)


def test_normalize_uses_the_range_of_each_criterion():
    assert norm(problem([[2, 10], [4, 30], [6, 20]])).tolist() == [[0, 0], [0.5, 1], [1, 0.5]]


def test_normalize_turns_lower_is_better_around():
    assert norm(problem([[2, 10], [4, 30], [6, 20]], direction=[0, 1]))[:, 0].tolist() == [1, 0.5, 0]


def test_flat_criterion_stops_with_its_name(pequeno):
    with pytest.raises(ValueError, match="C2"):
        pequeno.rank(problem([[1, 5], [2, 5]]), 2, 0.24)


def test_value_of_one_cell_of_matrix_b_by_hand():
    """Mesma conta da Equação 3.6: alternativas 2 e 4, critérios 2 e 3."""
    a = norm(SMALL)
    expected = (a[1, 1] + a[1, 2] + a[3, 1] + a[3, 2]) / 4 * ((0.5 + 0.8) / 2) * 0.9
    assert rule_of(SMALL, 2).combo_values([1, 3])[2] == pytest.approx(expected)


def test_matrix_b_has_one_column_per_group():
    rule = rule_of(SMALL, 2)
    assert rule.groups.tolist() == [list(g) for g in combinations(range(3), 2)]
    assert rule.combo_values([0, 1]).shape == (comb(3, 2),)


def test_three_choices_average_all_pairs_of_complementarity():
    """Equação 3.7: com 3 critérios, c' é a média dos 3 pares."""
    rule = rule_of(SMALL, 3)
    assert rule.groups.tolist() == [[0, 1, 2]]
    assert rule.factor[0] == pytest.approx(np.mean([1.0, 0.5, 0.8]) * np.mean([0.2, 0.6, 0.9]))


def test_value_equal_to_tau_passes(pequeno):
    assert pequeno.rank(problem([[0, 0], [1, 1]]), 2, 0.5)[0].share == 1


def test_value_equal_to_tau_passes_despite_floating_point(pequeno):
    data = problem([[0, 0], [1, 1]], weights=[0.1, 0.1], complementarity=[[0, 3], [3, 0]])
    assert pequeno.rank(data, 2, 0.15)[0].share == 1


def test_compensation_does_not_save_a_low_group(pequeno):
    """Um valor muito alto em um grupo não paga o grupo que ficou abaixo do tau."""
    data = problem([[1, 1, 0], [1, 1, 0], [0, 0, 1], [0.5, 0.5, 0.5]])
    shares = {choice.alternatives: choice.share for choice in pequeno.rank(data, 2, 0.6)}
    assert shares[("A1", "A2")] == pytest.approx(1 / 3)


def test_ties_share_the_position(pequeno):
    ranking = pequeno.rank(problem([[1, 0], [0, 1], [1, 0], [0, 0.5]]), 2, 0.5)
    tied = sum(choice.share == ranking[0].share for choice in ranking)
    assert tied > 1
    assert [choice.position for choice in ranking[:tied]] == [1] * tied
    assert ranking[tied].position == tied + 1


def test_ranking_goes_from_best_to_worst(pequeno):
    shares = [choice.share for choice in pequeno.rank(SMALL, 2, 0.2)]
    assert shares == sorted(shares, reverse=True)


@pytest.mark.parametrize("choices", [1, 0, -1, 4])
def test_invalid_number_of_choices(pequeno, choices):
    with pytest.raises(ValueError, match="de 2 a 3"):
        pequeno.check_size(SMALL, choices)


def test_large_problem_is_refused_before_it_runs(pequeno):
    wide = Problem(
        tuple(str(i) for i in range(5000)), tuple(str(j) for j in range(10)),
        np.zeros((1, 1)), np.ones(1), np.ones(1),
    )
    assert comb(5000, 2) * comb(10, 2) > MAX_EVALUATIONS
    with pytest.raises(ValueError, match="avaliações"):
        pequeno.check_size(wide, 2)


def test_example_is_small_and_lower_is_better_for_absences(pequeno):
    example = pequeno.load_problem()
    assert example.values.shape == (8, 6)
    assert example.direction[example.criteria.index("Faltas")] == 0
    assert np.array_equal(example.complementarity, example.complementarity.T)


def test_example_prefers_complement_over_the_two_best(pequeno):
    example = pequeno.load_problem()
    assert [name for name, _ in pequeno.individual_order(example)[:2]] == ["A1", "A2"]
    ranking = pequeno.rank(example, 2, 0.24)
    assert ("A1", "A3") in [c.alternatives for c in ranking if c.position == 1]
    assert ("A1", "A2") not in [c.alternatives for c in ranking if c.position == 1]


def test_program_prints_ranking_and_comparison(pequeno, capsys):
    pequeno.main([])
    output = capsys.readouterr().out
    assert "28 conjuntos e 15 grupos de critérios" in output
    assert "A1, A3" in output
    assert "3.º lugar no MEM" in output
    assert "Sensibilidade do tau" in output


def test_minimum_rule_also_runs(pequeno, capsys):
    pequeno.main(["--regra", "minimo", "--no-plot"])
    output = capsys.readouterr().out
    assert "regra minimo" in output
    assert "28 conjuntos e 15 grupos de critérios" in output


def test_unknown_rule_is_rejected(pequeno):
    with pytest.raises(SystemExit) as stop:
        pequeno.main(["--regra", "outra"])
    assert stop.value.code == 2


def test_radar_compares_the_usual_pair_with_the_mem_winner(pequeno):
    panels = pequeno.comparison_panels(pequeno.load_problem(), 2, 0.24)
    assert [names for _, names in panels] == [("A1", "A2"), ("A1", "A3")]
    assert panels[0][0].startswith("Média ponderada: A1, A2\n3.º no MEM, 60,0%")


def test_radar_has_one_panel_when_the_usual_pair_wins(pequeno):
    panels = pequeno.comparison_panels(pequeno.load_problem(), 2, 0.30)
    assert [names for _, names in panels] == [("A1", "A2")]


def test_radar_flag_saves_a_png(pequeno, tmp_path):
    target = tmp_path / "radar.png"
    pequeno.main(["--radar", str(target)])
    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_chart_window_opens_at_the_end_in_a_terminal(pequeno, monkeypatch, capsys):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    shown = []
    monkeypatch.setattr(pequeno, "interactive", lambda: True)
    monkeypatch.setattr(plt, "show", lambda: shown.append(len(plt.gcf().axes)))
    pequeno.main([])
    assert shown == [2]
    assert "Feche a janela" in capsys.readouterr().out


def test_no_plot_keeps_the_window_closed(pequeno, monkeypatch):
    import matplotlib.pyplot as plt

    monkeypatch.setattr(pequeno, "interactive", lambda: True)
    monkeypatch.setattr(plt, "show", lambda: pytest.fail("não deveria abrir a janela"))
    pequeno.main(["--no-plot"])


@pytest.mark.parametrize("argv", [["--choices", "9"], ["--top", "0"], ["--data", "nada"]])
def test_bad_options_stop_with_a_message(pequeno, argv):
    with pytest.raises(SystemExit) as stop:
        pequeno.main(argv)
    assert str(stop.value).startswith("Erro:")


@pytest.mark.parametrize("tau", ["0", "-1", "nan", "inf", "x"])
def test_invalid_tau(pequeno, tau, capsys):
    with pytest.raises(SystemExit) as stop:
        pequeno.main(["--tau", tau])
    assert stop.value.code == 2
    assert "tau" in capsys.readouterr().err

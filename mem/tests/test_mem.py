from itertools import combinations
from math import comb

import numpy as np
import pytest

from mem import (
    MAX_EVALUATIONS,
    Problem,
    check_size,
    comparison_panels,
    criteria_factors,
    individual_order,
    load_problem,
    main,
    matrix_b_prime,
    normalize,
    rank,
)


def problem(payment, direction=None, weights=None, complementarity=None):
    payment = np.array(payment, float)
    n_alternatives, n_criteria = payment.shape
    if complementarity is None:
        complementarity = np.ones((n_criteria, n_criteria)) - np.eye(n_criteria)
    return Problem(
        tuple(f"A{i + 1}" for i in range(n_alternatives)),
        tuple(f"C{j + 1}" for j in range(n_criteria)),
        payment,
        np.ones(n_criteria, int) if direction is None else np.array(direction),
        np.ones(n_criteria) if weights is None else np.array(weights, float),
        np.array(complementarity, float),
    )


SMALL = problem(
    [[10, 0, 4], [0, 10, 8], [5, 5, 0], [10, 10, 10]],
    weights=[1.0, 0.5, 0.8],
    complementarity=[[0, 0.2, 0.6], [0.2, 0, 0.9], [0.6, 0.9, 0]],
)


def test_normalize_uses_the_range_of_each_criterion():
    data = problem([[2, 10], [4, 30], [6, 20]])
    assert normalize(data).tolist() == [[0, 0], [0.5, 1], [1, 0.5]]


def test_normalize_turns_lower_is_better_around():
    data = problem([[2, 10], [4, 30], [6, 20]], direction=[0, 1])
    assert normalize(data)[:, 0].tolist() == [1, 0.5, 0]


def test_flat_criterion_stops_with_its_name():
    with pytest.raises(ValueError, match="C2"):
        normalize(problem([[1, 5], [2, 5]]))


def test_value_of_one_cell_of_matrix_b_by_hand():
    """Mesma conta da Equação 3.6: alternativas 2 e 4, critérios 2 e 3."""
    sets, values = matrix_b_prime(SMALL, 2)
    a = normalize(SMALL)
    expected = (a[1, 1] + a[1, 2] + a[3, 1] + a[3, 2]) / 4 * ((0.5 + 0.8) / 2) * 0.9
    assert values[sets.index((1, 3)), 2] == pytest.approx(expected)


def test_matrix_b_has_one_row_per_set_and_one_column_per_group():
    sets, values = matrix_b_prime(SMALL, 2)
    assert values.shape == (comb(4, 2), comb(3, 2))
    assert sets == list(combinations(range(4), 2))


def test_three_choices_average_all_pairs_of_complementarity():
    """Equação 3.7: com 3 critérios, c' é a média dos 3 pares."""
    groups, factors = criteria_factors(SMALL, 3)
    assert groups.tolist() == [[0, 1, 2]]
    assert factors[0] == pytest.approx(np.mean([1.0, 0.5, 0.8]) * np.mean([0.2, 0.6, 0.9]))


def test_value_equal_to_tau_passes():
    data = problem([[0, 0], [1, 1]])
    assert rank(data, 2, 0.5)[0].share == 1


def test_value_equal_to_tau_passes_despite_floating_point():
    data = problem([[0, 0], [1, 1]], weights=[0.1, 0.1], complementarity=[[0, 3], [3, 0]])
    assert rank(data, 2, 0.15)[0].share == 1


def test_compensation_does_not_save_a_low_group():
    """Um valor muito alto em um grupo não paga o grupo que ficou abaixo do tau."""
    data = problem([[1, 1, 0], [1, 1, 0], [0, 0, 1], [0.5, 0.5, 0.5]])
    shares = {choice.alternatives: choice.share for choice in rank(data, 2, 0.6)}
    assert shares[("A1", "A2")] == pytest.approx(1 / 3)


def test_ties_share_the_position():
    data = problem([[1, 0], [0, 1], [1, 0], [0, 0.5]])
    ranking = rank(data, 2, 0.5)
    tied = sum(choice.share == ranking[0].share for choice in ranking)
    assert tied > 1
    assert [choice.position for choice in ranking[:tied]] == [1] * tied
    assert ranking[tied].position == tied + 1


def test_ranking_goes_from_best_to_worst():
    shares = [choice.share for choice in rank(SMALL, 2, 0.2)]
    assert shares == sorted(shares, reverse=True)


@pytest.mark.parametrize("choices", [1, 0, -1, 4])
def test_invalid_number_of_choices(choices):
    with pytest.raises(ValueError, match="de 2 a 3"):
        check_size(SMALL, choices)


def test_large_problem_is_refused_before_it_runs():
    wide = Problem(
        tuple(str(i) for i in range(5000)), tuple(str(j) for j in range(10)),
        np.zeros((1, 1)), np.ones(1), np.ones(1), np.zeros((1, 1)),
    )
    assert comb(5000, 2) * comb(10, 2) > MAX_EVALUATIONS
    with pytest.raises(ValueError, match="avaliações"):
        check_size(wide, 2)


def test_example_is_small_and_lower_is_better_for_absences():
    example = load_problem()
    assert example.payment.shape == (8, 6)
    assert example.direction[example.criteria.index("Faltas")] == 0
    assert np.array_equal(example.complementarity, example.complementarity.T)


def test_example_prefers_complement_over_the_two_best():
    example = load_problem()
    assert [name for name, _ in individual_order(example)[:2]] == ["A1", "A2"]
    ranking = rank(example, 2, 0.24)
    assert ("A1", "A3") in [c.alternatives for c in ranking if c.position == 1]
    assert ("A1", "A2") not in [c.alternatives for c in ranking if c.position == 1]


def test_program_prints_ranking_and_comparison(capsys):
    main([])
    output = capsys.readouterr().out
    assert "28 conjuntos e 15 grupos de critérios" in output
    assert "A1, A3" in output
    assert "3.º lugar no MEM" in output
    assert "Sensibilidade do tau" in output


def test_radar_compares_the_usual_pair_with_the_mem_winner():
    panels = comparison_panels(load_problem(), 2, 0.24)
    assert [names for _, names in panels] == [("A1", "A2"), ("A1", "A3")]
    assert panels[0][0].startswith("Média ponderada: A1, A2\n3.º no MEM, 60,0%")


def test_radar_has_one_panel_when_the_usual_pair_wins():
    panels = comparison_panels(load_problem(), 2, 0.30)
    assert [names for _, names in panels] == [("A1", "A2")]


def test_radar_flag_saves_a_png(tmp_path):
    target = tmp_path / "radar.png"
    main(["--radar", str(target)])
    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.parametrize("argv", [["--choices", "9"], ["--top", "0"], ["--data", "nada"]])
def test_bad_options_stop_with_a_message(argv):
    with pytest.raises(SystemExit) as stop:
        main(argv)
    assert str(stop.value).startswith("Erro:")


@pytest.mark.parametrize("tau", ["0", "-1", "nan", "inf", "x"])
def test_invalid_tau(tau, capsys):
    with pytest.raises(SystemExit) as stop:
        main(["--tau", tau])
    assert stop.value.code == 2
    assert "tau" in capsys.readouterr().err

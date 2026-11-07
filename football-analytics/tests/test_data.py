import numpy as np
import pytest

from mem.pesos import complementarity_from_data as complementarity_matrix
from mem.pesos import group_weights as position_weights
from comum.jogadores import DataError, load_dataset, normalize


def write_dataset(folder, goalkeepers=None):
    (folder / "criteria.csv").write_text(
        "criterion,direction,weight\ngoals,1,1\nfouls,0,1\n", encoding="utf-8"
    )
    (folder / "players.csv").write_text(
        "player,team,position,minutes,goals,fouls\n"
        "Ana,X,A,900,10,2\nBia,X,A,1800,10,4\nCaio,Y,B,100,50,0\n",
        encoding="utf-8",
    )
    if goalkeepers:
        (folder / "goalkeepers.csv").write_text(goalkeepers, encoding="utf-8")


def test_real_data_shape(dataset):
    assert dataset.payment.shape == (317, 18)
    assert dataset.complementarity.shape == (18, 18)
    assert set(dataset.positions) == {"ATA", "LD", "LE", "MEI", "VOL", "ZAG"}


def test_normalize_keeps_values_between_zero_and_one(dataset):
    assert dataset.payment.min() == 0 and dataset.payment.max() == 1
    assert len(np.unique(dataset.payment)) > 2


def test_every_name_shows_the_club_code(dataset):
    assert all(name.endswith(")") and name[-5] == "(" for name in dataset.players)
    assert len(set(dataset.players)) == len(dataset.players)


def test_stats_are_compared_per_90_minutes(tmp_path):
    write_dataset(tmp_path)
    data = load_dataset(tmp_path, min_minutes=0)
    # Ana faz 1 gol por 90 minutos, Bia 0,5 e Caio 45.
    assert data.payment[:, 0] == pytest.approx([0.5 / 44.5, 0, 1])


def test_old_criteria_file_with_cut_still_works(tmp_path):
    # criteria.csv com a coluna cut preenchida carrega normalmente, e a coluna é ignorada.
    write_dataset(tmp_path)
    without_cut = load_dataset(tmp_path, min_minutes=0)
    (tmp_path / "criteria.csv").write_text(
        "criterion,direction,weight,cut\ngoals,1,1,5\nfouls,0,1,\n", encoding="utf-8"
    )
    with_cut = load_dataset(tmp_path, min_minutes=0)
    assert with_cut.payment == pytest.approx(without_cut.payment)


def test_players_below_the_minimum_minutes_stay_out(tmp_path):
    write_dataset(tmp_path)
    data = load_dataset(tmp_path, min_minutes=850)
    assert data.players == ["Ana (X)", "Bia (X)"]


GOALKEEPERS = (
    "player,team,minutes,saves,goals_conceded,"
    "long_passes_accurate,long_passes_inaccurate,clearances\n"
    "Rui,X,900,90,10,10,90,1\n"
    "Leo,Y,900,70,30,90,10,50\n"
    "Ivo,Z,900,60,40,20,80,2\n"
    "Bia,W,900,50,50,30,70,3\n"
    "Ana,V,900,40,60,40,60,4\n"
    "Teo,U,100,99,1,99,1,99\n"
)


def test_goalkeeper_with_more_criteria_wins(tmp_path):
    write_dataset(tmp_path, GOALKEEPERS)
    data = load_dataset(tmp_path, min_minutes=850)
    assert data.goalkeeper["name"] == "Leo (Y)"
    assert data.goalkeeper["hits"] == 2


def test_goalkeeper_tie_goes_to_the_best_save_rate(tmp_path):
    write_dataset(tmp_path, GOALKEEPERS.replace("Leo,Y,900,70,30,90,10,50", "Leo,Y,900,70,30,90,10,1"))
    data = load_dataset(tmp_path, min_minutes=850)
    assert data.goalkeeper["name"] == "Rui (X)"


def test_goalkeeper_file_is_optional(tmp_path):
    write_dataset(tmp_path)
    assert load_dataset(tmp_path, min_minutes=0).goalkeeper is None


def test_complementarity_ignores_differences_between_positions():
    # Entre posições, os critérios sobem juntos. Dentro de cada posição, não têm relação.
    values = np.array([[0, 1], [2, 1], [0, 3], [2, 3], [10, 11], [12, 11], [10, 13], [12, 13.0]])
    positions = np.array(["A"] * 4 + ["B"] * 4)
    assert complementarity_matrix(values, positions)[0, 1] == pytest.approx(1)


def test_related_criteria_have_low_complementarity():
    values = np.array([[1, 2], [2, 4], [3, 6], [4, 9.0]])
    positions = np.array(["A"] * 4)
    assert complementarity_matrix(values, positions)[0, 1] < 0.05


def test_constant_criterion_has_full_complementarity():
    values = np.array([[1, 5], [2, 5], [3, 5.0]])
    assert complementarity_matrix(values, np.array(["A"] * 3))[0, 1] == 1


def test_position_weights_favor_what_the_position_does_more():
    values = np.array([[10, 1], [12, 1], [1, 10], [1, 12.0]])
    positions = np.array(["A", "A", "B", "B"])
    weights = position_weights(values, positions, [1, 1])
    assert weights[0, 0] > weights[0, 1]
    assert weights[2, 1] > weights[2, 0]
    assert weights.mean(axis=1) == pytest.approx(1)


def test_cost_criteria_get_no_bonus():
    values = np.array([[10, 1], [12, 1], [1, 10], [1, 12.0]])
    weights = position_weights(values, np.array(["A", "A", "B", "B"]), [0, 1])
    assert weights[0, 0] == pytest.approx(weights[0, 1])


def test_single_position_keeps_equal_weights():
    weights = position_weights(np.array([[1, 2], [3, 4.0]]), np.array(["A", "A"]), [1, 1])
    assert weights.tolist() == [[1, 1], [1, 1]]


def test_real_weights_make_football_sense(dataset):
    def top(position):
        row = dataset.player_weights[dataset.positions == position][0]
        return dataset.criteria[int(row.argmax())]

    assert top("ZAG") == "Clearences"
    assert top("ATA") == "GolsA"


def test_cost_criterion_is_inverted():
    result = normalize(np.array([[0.0], [5.0], [10.0]]), [0])
    assert result.ravel().tolist() == [1.0, 0.5, 0.0]


def test_constant_criterion_does_not_divide_by_zero():
    result = normalize([[4], [4]], [1])
    assert np.isfinite(result).all()


def test_missing_file_has_a_clear_error(tmp_path):
    with pytest.raises(DataError, match="criteria.csv"):
        load_dataset(tmp_path)

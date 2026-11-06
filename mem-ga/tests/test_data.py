import numpy as np
import pytest

from mem_ga import DataError, load_dataset, normalize


def write_dataset(folder, goalkeepers=None):
    (folder / "criteria.csv").write_text(
        "criterion,direction,weight,cut\ngoals,1,1,\nfouls,0,1,\n", encoding="utf-8"
    )
    (folder / "players.csv").write_text(
        "player,team,position,minutes,goals,fouls\n"
        "Ana,X,A,900,10,2\nBia,X,A,1800,10,4\nCaio,Y,B,100,50,0\n",
        encoding="utf-8",
    )
    (folder / "matrix_c.csv").write_text(
        "criterion,goals,fouls\ngoals,,0.5\nfouls,,\n", encoding="utf-8"
    )
    if goalkeepers:
        (folder / "goalkeepers.csv").write_text(goalkeepers, encoding="utf-8")


def test_real_data_shape(dataset):
    assert dataset.payment.shape == (317, 18)
    assert dataset.complementarity.shape == (18, 18)
    assert set(dataset.positions) == {"ATA", "LD", "LE", "MEI", "VOL", "ZAG"}


def test_about_a_fifth_of_the_players_reach_each_cut(dataset):
    # Critérios de custo são invertidos, então neles a maioria fica com 1.
    share = dataset.payment.mean(axis=0)
    assert np.minimum(share, 1 - share) == pytest.approx(0.2, abs=0.03)


def test_every_name_shows_the_club_code(dataset):
    assert all(name.endswith(")") and name[-5] == "(" for name in dataset.players)
    assert len(set(dataset.players)) == len(dataset.players)


def test_stats_are_compared_per_90_minutes(tmp_path):
    write_dataset(tmp_path)
    data = load_dataset(tmp_path, min_minutes=0)
    # Ana faz 1 gol por 90 minutos, Bia 0,5 e Caio 45.
    assert data.payment[:, 0] == pytest.approx([0.5 / 44.5, 0, 1])


def test_players_below_the_minimum_minutes_stay_out(tmp_path):
    write_dataset(tmp_path)
    data = load_dataset(tmp_path, min_minutes=850)
    assert data.players == ["Ana (X)", "Bia (X)"]


def test_goalkeeper_is_the_one_with_the_best_save_rate(tmp_path):
    write_dataset(
        tmp_path,
        "player,team,minutes,saves,goals_conceded\n"
        "Rui,X,900,60,40\nLeo,Y,900,80,20\nTeo,Z,100,99,1\n",
    )
    data = load_dataset(tmp_path, min_minutes=850)
    assert data.goalkeeper == "Leo (Y)"
    assert data.goalkeeper_save_rate == pytest.approx(0.8)


def test_goalkeeper_file_is_optional(tmp_path):
    write_dataset(tmp_path)
    assert load_dataset(tmp_path, min_minutes=0).goalkeeper is None


def test_cut_marks_values_at_or_above_it():
    result = normalize([[1], [2], [3]], [1], [2])
    assert result.ravel().tolist() == [0, 1, 1]


def test_cost_criterion_is_inverted():
    result = normalize([[1], [2], [3]], [0], [2])
    assert result.ravel().tolist() == [1, 0, 0]


def test_blank_cut_keeps_the_criterion_continuous():
    result = normalize([[0], [5], [10]], [1], [np.nan])
    assert result.ravel().tolist() == [0, 0.5, 1]


def test_constant_criterion_does_not_divide_by_zero():
    result = normalize([[4], [4]], [1], [np.nan])
    assert np.isfinite(result).all()


def test_missing_file_has_a_clear_error(tmp_path):
    with pytest.raises(DataError, match="criteria.csv"):
        load_dataset(tmp_path)

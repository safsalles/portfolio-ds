import pytest

from verificador.calculator import breakeven_milheiro, compare


def test_breakeven_matches_reference():
    assert breakeven_milheiro(19152, 502000, 3000) == pytest.approx(32.17, abs=0.01)


def test_compare_milheiro_100_loses():
    result = compare(19152, 502000, 100, 3000)

    assert result.miles_win is False
    assert result.miles_cost_brl == 53200


def test_compare_milheiro_30_wins():
    result = compare(19152, 502000, 30, 3000)

    assert result.miles_win is True
    assert result.savings_brl == pytest.approx(19152 - (502 * 30 + 3000))


def test_miles_zero_raises_valueerror():
    with pytest.raises(ValueError):
        breakeven_milheiro(19152, 0, 3000)
    with pytest.raises(ValueError):
        compare(19152, 0, 30, 3000)

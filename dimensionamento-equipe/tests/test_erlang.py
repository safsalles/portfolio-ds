import math
from fractions import Fraction

import pytest

from src.erlang import (
    agents_needed,
    average_speed_of_answer,
    erlang_c,
    service_level,
)


def reference_erlang_c(a: int, n: int) -> float:
    """Fórmula direta com frações exatas (independente da recorrência)."""
    top = Fraction(a) ** n / math.factorial(n) * Fraction(n, n - a)
    bottom = sum(Fraction(a) ** k / math.factorial(k) for k in range(n)) + top
    return float(top / bottom)


def test_mm1():
    assert erlang_c(0.5, 1) == pytest.approx(0.5)


def test_two_agents_one_erlang():
    assert erlang_c(1.0, 2) == pytest.approx(1 / 3)


@pytest.mark.parametrize("a", [2, 10, 50, 200])
def test_matches_exact_reference(a):
    for n in range(a + 1, a + 6):
        assert erlang_c(a, n) == pytest.approx(reference_erlang_c(a, n), rel=1e-9)


def test_service_level_mm1():
    assert service_level(0.5, 1, aht_s=360, wait_s=0) == pytest.approx(0.5)


def test_unstable_queue():
    assert service_level(5, 5, 360, 20) == 0.0
    assert erlang_c(6, 5) == 1.0


def test_zero_traffic():
    assert agents_needed(0, 360, 0.8, 20) == 0
    assert service_level(0, 3, 360, 20) == 1.0


def test_monotonic():
    values = [service_level(10, n, 360, 20) for n in range(11, 31)]
    assert all(b >= a for a, b in zip(values, values[1:]))


def test_agents_needed_meets_target_minimally():
    n = agents_needed(200, 360, 0.8, 20)
    a = 200 * 360 / 3600
    assert service_level(a, n, 360, 20) >= 0.8
    assert service_level(a, n - 1, 360, 20) < 0.8


def test_shrinkage():
    base = agents_needed(200, 360, 0.8, 20)
    assert agents_needed(200, 360, 0.8, 20, shrinkage=0.30) == math.ceil(base / 0.7)


def test_large_traffic_no_overflow():
    assert 0.0 <= erlang_c(300, 310) <= 1.0


def test_stricter_target_needs_more():
    assert agents_needed(200, 360, 0.9, 20) >= agents_needed(200, 360, 0.8, 20)


def test_asa_unstable_is_inf_and_stable_is_finite():
    assert average_speed_of_answer(5, 5, 360) == math.inf
    assert math.isfinite(average_speed_of_answer(5, 7, 360))

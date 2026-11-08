import numpy as np
import pytest

from mem.pesos import complementarity_from_data, group_weights


@pytest.fixture
def three_groups():
    rng = np.random.default_rng(0)
    values = rng.normal(size=(30, 4))
    groups = np.repeat(["g1", "g2", "g3"], 10)
    values[groups == "g2"] += [3, 0, 0, 0]
    return values, groups


def test_diagonal_da_complementacao_e_zero(three_groups):
    values, groups = three_groups
    assert np.allclose(np.diag(complementarity_from_data(values, groups)), 0)


def test_criterios_iguais_dentro_do_grupo_nao_se_complementam():
    groups = np.array(["g1"] * 3 + ["g2"] * 3)
    first = np.array([1.0, 2, 3, 10, 20, 30])
    values = np.column_stack([first, first * 2])
    assert complementarity_from_data(values, groups)[0, 1] == pytest.approx(0)


def test_sem_grupos_e_um_menos_a_correlacao_em_modulo(three_groups):
    values, _ = three_groups
    expected = 1 - np.abs(np.corrcoef(values, rowvar=False))
    assert np.allclose(complementarity_from_data(values), expected)


def test_correlacao_e_calculada_dentro_de_cada_grupo():
    # Entre os grupos os dois critérios sobem juntos, mas dentro deles são opostos.
    groups = np.array(["g1", "g1", "g2", "g2"])
    values = np.array([[0.0, 1], [1, 0], [10, 11], [11, 10]])
    assert complementarity_from_data(values, groups)[0, 1] == pytest.approx(0)
    assert complementarity_from_data(values)[0, 1] < 0.1


def test_pesos_por_grupo_tem_media_um_em_cada_grupo(three_groups):
    values, groups = three_groups
    weights = group_weights(values, groups, np.ones(4))
    for group in ("g1", "g2", "g3"):
        assert weights[groups == group].mean(axis=1) == pytest.approx(1)


def test_grupo_forte_num_criterio_ganha_peso_nele(three_groups):
    values, groups = three_groups
    weights = group_weights(values, groups, np.ones(4))
    assert weights[groups == "g2"][0, 0] > weights[groups == "g2"][0, 1]


def test_um_grupo_so_deixa_todos_os_pesos_em_um():
    values = np.array([[1.0, 2], [3, 4]])
    assert np.array_equal(group_weights(values, np.array(["g", "g"]), [1, 1]), np.ones((2, 2)))

from pathlib import Path

import numpy as np
import pytest

from mem.problema import Problem, load_problem, normalize

DATA = Path(__file__).resolve().parents[1] / "exemplos" / "recrutamento-pequeno" / "data"


def test_normalize_inverte_criterio_de_custo():
    values = np.array([[1.0, 10.0], [3.0, 20.0], [2.0, 30.0]])
    got = normalize(values, np.array([1, 0]))
    assert np.allclose(got, [[0, 1], [1, 0.5], [0.5, 0]])


def test_coluna_constante_vira_zero_quando_permitida():
    values = np.array([[1.0, 5.0], [3.0, 5.0]])
    got = normalize(values, np.array([1, 1]))
    assert np.array_equal(got, [[0.0, 0.0], [1.0, 0.0]])


def test_coluna_constante_da_erro_quando_proibida():
    values = np.array([[1.0, 5.0], [3.0, 5.0]])
    with pytest.raises(ValueError, match="Critério com o mesmo valor em todas as alternativas: b."):
        normalize(values, np.array([1, 1]), allow_constant=False, criteria=["a", "b"])


def test_load_problem_le_o_exemplo_pequeno():
    problem = load_problem(DATA)
    assert isinstance(problem, Problem)
    assert len(problem.alternatives) == 8
    assert len(problem.criteria) == 6
    assert problem.values.shape == (8, 6)
    assert problem.groups is None
    assert problem.complementarity.shape == (6, 6)
    assert np.array_equal(problem.complementarity, problem.complementarity.T)
    assert problem.weights.shape == (6,)
    assert (problem.weights > 0).all()


def _write(folder, name, text):
    (folder / name).write_text(text, encoding="utf-8")


def test_load_problem_le_grupos_e_aceita_sem_complementacao(tmp_path):
    _write(tmp_path, "criteria.csv", "criterion,direction,weight\na,1,1\nb,0,2\n")
    _write(tmp_path, "alternatives.csv", "alternative,group,a,b\nx,g1,1,2\ny,g2,3,4\n")
    problem = load_problem(tmp_path)
    assert problem.groups.tolist() == ["g1", "g2"]
    assert problem.complementarity is None
    assert problem.direction.tolist() == [1, 0]
    assert problem.weights.tolist() == [1.0, 2.0]


def test_load_problem_cita_o_arquivo_que_falta(tmp_path):
    _write(tmp_path, "criteria.csv", "criterion,direction,weight\na,1,1\n")
    with pytest.raises(ValueError, match="alternatives.csv"):
        load_problem(tmp_path)


def test_load_problem_cita_a_coluna_que_falta(tmp_path):
    _write(tmp_path, "criteria.csv", "criterion,direction,weight\na,1,1\nb,1,1\n")
    _write(tmp_path, "alternatives.csv", "alternative,a\nx,1\n")
    with pytest.raises(ValueError, match="alternatives.csv.*b"):
        load_problem(tmp_path)

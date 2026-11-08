from collections import Counter

import numpy as np
import pytest

from mem.busca import traditional_choice
from mem.regras import build_rule


def test_mesma_semente_da_os_mesmos_dados(gerador):
    assert gerador.generate(2026) == gerador.generate(2026)


def test_outra_semente_da_outros_dados(gerador):
    assert gerador.generate(2026) != gerador.generate(7)


def test_csvs_gravados_batem_com_o_gerador(gerador, grande):
    criteria, candidates = gerador.generate(2026)
    problem = grande.load_problem()
    assert list(problem.criteria) == [row["criterion"] for row in criteria]
    assert list(problem.alternatives) == [row["alternative"] for row in candidates]
    expected = np.array([[row[name] for name in problem.criteria] for row in candidates], float)
    assert np.array_equal(problem.values, expected)
    assert problem.groups.tolist() == [row["group"] for row in candidates]


def test_trezentos_candidatos_em_tres_cargos(grande):
    problem = grande.load_problem()
    assert problem.values.shape == (300, 8)
    assert Counter(problem.groups.tolist()) == {"analista": 150, "engenheiro": 90, "gestor": 60}
    assert problem.criteria == (
        "sql", "estatistica", "visualizacao", "programacao",
        "comunicacao", "lideranca", "negociacao", "organizacao",
    )


def test_avaliacoes_de_0_a_10_sem_coluna_constante(grande):
    values = grande.load_problem().values
    assert values.min() >= 0 and values.max() <= 10
    assert np.array_equal(values, np.round(values, 1))
    assert (values.std(axis=0) > 0).all()


def test_cada_cargo_tem_um_perfil_proprio(grande):
    problem = grande.load_problem()
    means = {g: problem.values[problem.groups == g].mean(axis=0) for g in ("analista", "gestor")}
    sql, lideranca = problem.criteria.index("sql"), problem.criteria.index("lideranca")
    assert means["analista"][sql] > means["gestor"][sql]
    assert means["gestor"][lideranca] > means["analista"][lideranca]


@pytest.mark.parametrize("regra", ["media", "minimo"])
def test_tau_gravado_deixa_a_escolha_tradicional_no_meio(grande, regra):
    problem = grande.load_problem()
    rule = build_rule(problem, regra, grande.TAU[regra], size=grande.SIZE)
    team = traditional_choice(rule.payment, grande.SIZE, problem.groups, grande.QUOTAS)
    assert 0.40 <= rule.rate(team)[0] <= 0.60


def test_vagas_somam_o_tamanho_da_equipe(grande):
    assert grande.QUOTAS == {"analista": 2, "engenheiro": 1, "gestor": 1}
    assert grande.SIZE == 4


def test_programa_mostra_as_tres_equipes(grande, capsys):
    grande.main(["--seed", "1", "--no-plot", "--iterations", "300"])
    output = capsys.readouterr().out
    assert "Regra media" in output
    assert "Regra minimo" in output
    assert "Escolha tradicional" in output
    assert "70 grupos" in output


def test_radar_salva_um_png(grande, tmp_path):
    target = tmp_path / "radar.png"
    grande.main(["--seed", "1", "--iterations", "300", "--radar", str(target)])
    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

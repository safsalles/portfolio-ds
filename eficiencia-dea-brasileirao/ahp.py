"""Pesos por categoria de cada posição, a partir das respostas AHP (ahp_respostas.json).

AHP com comparações incompletas (Harker, 1987): cada resposta diz quantas vezes a categoria de referência
pesa mais que outra; o peso de cada categoria é proporcional a 1/razão (a referência vale 1).
"""
import json
import os

T = "matchstats.headers.tackles"
DEF_ATQ = ["recoveries", T, "interceptions"]
CATEGORIAS = {  # categoria -> colunas de output (as cortadas por correlação são ignoradas)
    "Atacante": {"Gols": ["goals"], "Assistências": ["assists"],
                 "Criação": ["big_chance_created_team_title", "chances_created"],
                 "Defesa": DEF_ATQ, "Erros": ["menos_erros"]},
    "Ponta": {"Gols": ["goals"], "Assistências": ["assists"],
              "Criação": ["big_chance_created_team_title", "chances_created", "dribbles_succeeded",
                          "accurate_crosses", "line_breaking_passes", "was_fouled", "penalties_won"],
              "Defesa": DEF_ATQ, "Erros": ["menos_erros"]},
    "Meia atacante": {"Gols": ["goals"], "Assistências": ["assists"],
                      "Criação": ["big_chance_created_team_title", "chances_created", "line_breaking_passes",
                                  "penalties_won"],
                      "Defesa": DEF_ATQ, "Erros": ["menos_erros"]},
    "Volante": {"Defesa": DEF_ATQ + ["clearances", "aerials_won"], "Passe": ["accurate_passes", "long_balls_accurate"],
                "Assistências": ["assists"], "Erros": ["menos_erros"]},
    "Lateral": {"Defesa": DEF_ATQ + ["clearances", "aerials_won"],
                "Apoio": ["accurate_crosses", "dribbles_succeeded", "line_breaking_passes", "chances_created"],
                "Assistências": ["assists"], "Erros": ["menos_erros"]},
    "Zagueiro": {"Defesa no chão": DEF_ATQ, "Área": ["clearances", "shot_blocks"], "Jogo aéreo": ["aerials_won"],
                 "Saída de bola": ["long_balls_accurate", "accurate_passes", "line_breaking_passes"],
                 "Erros": ["menos_erros"]},
    "Goleiro": {"Defesas": ["saves", "goals_prevented"],
                "Domínio da área": ["keeper_high_claim", "keeper_sweeper", "punches"],
                "Passe": ["long_balls_accurate", "accurate_passes", "line_breaking_passes"]},
}
_R = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ahp_respostas.json"), encoding="utf-8"))


def pesos(posicao):
    resp = _R[posicao]
    bruto = {resp["referencia"]: 1.0, **{k: 1.0 / v for k, v in resp["razoes"].items()}}
    assert set(bruto) == set(CATEGORIAS[posicao]), (posicao, sorted(bruto))
    total = sum(bruto.values())
    return {k: v / total for k, v in bruto.items()}


def grupos(posicao, colunas):
    """(lista de índices de coluna, peso AHP) por categoria; exige que toda coluna tenha exatamente uma."""
    w = pesos(posicao)
    out = [([i for i, c in enumerate(colunas) if c in cols], w[k]) for k, cols in CATEGORIAS[posicao].items()]
    assert sorted(i for idx, _ in out for i in idx) == list(range(len(colunas))), (posicao, colunas)
    assert all(idx for idx, _ in out), (posicao, colunas)
    return out

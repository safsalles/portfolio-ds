"""Critérios do DEA por grupo de posição (v3: volante, lateral, zagueiro e goleiro escolhidos pelo Sérgio). Colunas de base_analise_2026.csv.

O DEA usa totais da temporada, com minutos como input; taxas por 90 só para tabelas e gráficos. Direção "-" = quanto menos, melhor (vira positivo pela
transformação do artigo de 2018: multiplicar por -1 e somar o módulo do menor valor).
"""

INPUTS = ["minutos", "valor_elenco_clube_eur"]  # no DEA o valor do clube entra em log10 (ver 03_rodar_dea.py)

# Input extra dos grupos de ataque: xG + xA somados num input só (qualidade das chances de finalizar e de
# assistir). Separados, davam 4 inputs e quase todos os atacantes ficavam eficientes.
# A validação externa (gols - xG, assistências - xA) é uma análise separada, sem DEA.
INPUTS_ATAQUE = ["xg_mais_xa"]
GRUPOS_ATAQUE = ["Atacante", "Ponta E", "Ponta D", "Meia atacante"]

# (coluna, direção). As variáveis "-" de cada posição são somadas (taxa por 90) num índice único de
# erros antes do DEA: uma a uma, cada uma virava um jeito a mais de ser "o melhor do grupo".
# (coluna, direção)
OUTPUTS_COMPLETOS = {
    "Atacante": [
        ("goals", "+"), ("assists", "+"), ("big_chance_created_team_title", "+"), ("chances_created", "+"),
        ("recoveries", "+"), ("matchstats.headers.tackles", "+"), ("interceptions", "+"),
        ("dispossessed", "-"), ("Offsides", "-"), ("big_chance_missed_title", "-"), ("fouls", "-"),
    ],
    "Ponta E": [
        ("goals", "+"), ("assists", "+"), ("big_chance_created_team_title", "+"), ("chances_created", "+"),
        ("dribbles_succeeded", "+"), ("accurate_crosses", "+"), ("line_breaking_passes", "+"),
        ("was_fouled", "+"), ("recoveries", "+"), ("matchstats.headers.tackles", "+"), ("interceptions", "+"),
        ("dispossessed", "-"), ("big_chance_missed_title", "-"), ("fouls", "-"),
    ],
    "Meia atacante": [
        ("goals", "+"), ("assists", "+"), ("big_chance_created_team_title", "+"), ("chances_created", "+"),
        ("line_breaking_passes", "+"), ("penalties_won", "+"), ("recoveries", "+"), ("matchstats.headers.tackles", "+"),
        ("dispossessed", "-"), ("Offsides", "-"), ("big_chance_missed_title", "-"), ("fouls", "-"),
    ],
    "Volante": [
        ("accurate_passes", "+"), ("long_balls_accurate", "+"), ("recoveries", "+"), ("matchstats.headers.tackles", "+"),
        ("interceptions", "+"), ("duel_won", "+"), ("aerials_won", "+"), ("clearances", "+"), ("assists", "+"),
        ("fouls", "-"), ("dispossessed", "-"), ("dribbled_past", "-"),
    ],
    "Lateral E": [
        ("accurate_crosses", "+"), ("dribbles_succeeded", "+"), ("chances_created", "+"), ("assists", "+"),
        ("line_breaking_passes", "+"), ("matchstats.headers.tackles", "+"), ("recoveries", "+"), ("interceptions", "+"), ("duel_won", "+"),
        ("clearances", "+"), ("aerials_won", "+"),
        ("dribbled_past", "-"), ("fouls", "-"), ("dispossessed", "-"),
    ],
    "Zagueiro D": [
        ("clearances", "+"), ("interceptions", "+"), ("shot_blocks", "+"), ("aerials_won", "+"), ("recoveries", "+"),
        ("matchstats.headers.tackles", "+"), ("duel_won", "+"), ("long_balls_accurate", "+"), ("accurate_passes", "+"), ("line_breaking_passes", "+"),
        ("dribbled_past", "-"), ("fouls", "-"), ("dispossessed", "-"),
    ],
    "Goleiro": [
        ("saves", "+"), ("goals_prevented", "+"), ("keeper_high_claim", "+"), ("keeper_sweeper", "+"),
        ("punches", "+"), ("long_balls_accurate", "+"), ("accurate_passes", "+"), ("line_breaking_passes", "+"),
    ],
}
# lados espelhados usam o mesmo critério
OUTPUTS_COMPLETOS["Ponta D"] = OUTPUTS_COMPLETOS["Ponta E"]
OUTPUTS_COMPLETOS["Lateral D"] = OUTPUTS_COMPLETOS["Lateral E"]
OUTPUTS_COMPLETOS["Zagueiro E"] = OUTPUTS_COMPLETOS["Zagueiro D"]

# outputs usados no DEA: a lista completa menos os redundantes de cada posição (gerado por 02_correlacao.py)
import json as _json
import os as _os
_arq = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "cortes.json")
_cortes = _json.load(open(_arq)) if _os.path.exists(_arq) else {}
OUTPUTS = {g: [(c, d) for c, d in o if c not in [x[0] for x in _cortes.get(g.removesuffix(" E").removesuffix(" D"), [])]]
           for g, o in OUTPUTS_COMPLETOS.items()}

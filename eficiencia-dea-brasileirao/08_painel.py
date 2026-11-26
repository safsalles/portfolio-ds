"""Gera o painel interativo (painel/index.html) a partir dos resultados do 03, 04 e 07.

A página leva só resultados do modelo e posições relativas dentro do grupo. Estatísticas brutas por
jogador e valores de mercado individuais ficam de fora (o valor aparece como % da mediana do grupo).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import ahp
import criterios as c

AQUI = Path(__file__).parent
codigo = (AQUI / "03_rodar_dea.py").read_text(encoding="utf-8").split("b = pd.read_csv")[0]
ns = {}
exec(codigo, ns)  # reaproveita o preparo das variáveis do 03
outputs_dea, taxa = ns["outputs_dea"], ns["taxa"]

BASE = sys.argv[1] if len(sys.argv) > 1 else "../../dados-fotmob/consolidado/br40"
ORDEM = ["Atacante", "Ponta", "Meia atacante", "Volante", "Lateral", "Zagueiro", "Goleiro"]
NOMES = {"goals": "gols", "assists": "assistências", "big_chance_created_team_title": "grandes chances criadas",
         "chances_created": "chances criadas", "recoveries": "recuperações", "matchstats.headers.tackles": "desarmes",
         "interceptions": "interceptações", "dribbles_succeeded": "dribles certos",
         "accurate_crosses": "cruzamentos certos", "line_breaking_passes": "passes que quebram linha",
         "was_fouled": "faltas sofridas", "penalties_won": "pênaltis sofridos", "accurate_passes": "passes certos",
         "long_balls_accurate": "passes longos certos", "aerials_won": "duelos aéreos ganhos", "duel_won": "duelos ganhos",
         "clearances": "cortes", "shot_blocks": "bloqueios", "saves": "defesas", "goals_prevented": "gols evitados",
         "keeper_high_claim": "bolas altas", "keeper_sweeper": "saídas do gol", "punches": "socos",
         "menos_erros": "menos erros"}


def num(v, casas=3):
    return None if v is None or not np.isfinite(v) else round(float(v), casas)


r = pd.read_csv(f"{BASE}/resultados_dea_2026.csv")
d = pd.read_csv(f"{BASE}/criterio_decisivo.csv").set_index("jogador_id")
cl = pd.read_csv(f"{BASE}/clubes_eficiencia_2026.csv")
b = pd.read_csv(f"{BASE}/base_analise_2026.csv")
a = b[b.acima_mediana & b.grupo.notna()].copy()
assert r.jogador_id.is_unique and len(r) == len(a) and len(d) == int(r.eficiente.sum())

# posição relativa (percentil 0-100) em cada categoria do AHP, por taxa a cada 90 minutos
relativa = {}
for g, x in a.groupby("grupo_lado"):
    x = x.reset_index(drop=True)
    pos = x.grupo[0].removesuffix(" E").removesuffix(" D")
    Y = outputs_dea(x, c.OUTPUTS[g])
    por90 = Y.div(x.minutos, axis=0)
    pct = por90.rank(pct=True) * 100
    cats = ahp.grupos(pos, list(Y.columns))
    for k, jid in enumerate(x.jogador_id):
        relativa[jid] = [[nome, round(w * 100), round(float(pct.iloc[k, idx].mean()))]
                         for nome, (idx, w) in zip(ahp.CATEGORIAS[pos], cats)]

mediana_valor = r.groupby("grupo_lado").valor_mercado_eur.median()
tamanho = r.groupby("grupo_lado").size()


def traduz(texto):
    if not isinstance(texto, str):
        return []
    saida = []
    for item in texto.split("; "):
        col, _, folga = item.partition(" (")
        saida.append(NOMES.get(col, col) + (" (" + folga if folga else ""))
    return saida


jogadores = []
for j in r.itertuples():
    pos = j.grupo_lado.removesuffix(" E").removesuffix(" D")
    o = {"id": int(j.jogador_id), "nome": j.nome, "time": j.time, "serie": j.divisao_2026[-1], "pos": pos,
         "grupo": j.grupo_lado, "n": int(tamanho[j.grupo_lado]),
         "nota": num(j.restrito), "leve": num(j.restrito_leve), "livre": num(j.ccr), "cruzada": num(j.cruzada),
         "rank": int(j.rank_restrito), "rankCruzada": int(j.rank_cruzada), "ef": bool(j.eficiente),
         "valorPct": num(j.valor_mercado_eur / mediana_valor[j.grupo_lado] * 100, 0),
         "cats": relativa[j.jogador_id],
         "ref": j.referencias.split("; ") if isinstance(j.referencias, str) else [],
         "melhorar": traduz(j.melhorar_em)}
    if j.jogador_id in d.index:
        e = d.loc[j.jogador_id]
        o["acima"] = num(e.acima_da_fronteira)
        o["decisivo"] = e.decisivo
        o["sem"] = [[k, num(e[f"sem {k}"])] for k in ahp.CATEGORIAS[pos]]
    jogadores.append(o)

clubes = [{"time": x.time, "serie": x.divisao_2026[-1], "avaliados": int(x.avaliados),
           "eficientes": int(x.eficientes), "pct": num(x.pct_eficientes * 100, 1), "nota": num(x.nota_media),
           "pts": num(x.pts_por_jogo, 2), "colocacao": int(x.posicao)} for x in cl.itertuples()]

dados = {"ordem": ORDEM, "jogadores": jogadores, "clubes": clubes}
texto = json.dumps(dados, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
modelo = (AQUI / "painel" / "modelo.html").read_text(encoding="utf-8")
assert modelo.count("__DADOS__") == 1
(AQUI / "painel" / "index.html").write_text(modelo.replace("__DADOS__", texto), encoding="utf-8")
print(f"painel/index.html: {len(jogadores)} jogadores, {sum(j['ef'] for j in jogadores)} eficientes, {len(clubes)} clubes")

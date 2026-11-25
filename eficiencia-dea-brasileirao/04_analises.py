"""Análises sobre resultados_dea_2026.csv: comparação entre métodos, xG, hipóteses e clubes.

Modelo principal: CCR com restrição de pesos ("restrito"); eficiente = nota 1 nele.

1. Métodos: correlação de Spearman entre os rankings (restrito, CCR, BCC, supereficiência, cruzada, TOPSIS) por grupo.
2. xG: gols - xG e assistências - xA por 90 (sem DEA) contra o modelo principal, nos grupos de ataque.
3. H1 (valor de mercado) e H2 (idade), como no artigo de 2018, com Pearson e Spearman por grupo.
4. Clubes: eficientes por clube contra pontos por jogo, posição e valor do elenco; Série A contra Série B.
5. Oportunidades: eficientes no modelo principal com valor de mercado abaixo da mediana do grupo,
   ordenados pela eficiência cruzada.
"""
import gzip
import json
import sys

import pandas as pd

BASE = sys.argv[1] if len(sys.argv) > 1 else "../../dados-fotmob/consolidado/br40"
LIGAS = sys.argv[2] if len(sys.argv) > 2 else "../../dados-fotmob/ligas"
r = pd.read_csv(f"{BASE}/resultados_dea_2026.csv")
pd.set_option("display.width", 200)
METODOS = ["restrito", "ccr", "bcc", "supereficiencia", "cruzada", "topsis"]
ATAQUE = ["Atacante", "Ponta E", "Ponta D", "Meia atacante"]


def classe(v):  # tabela de Chowdhury et al. (2015), usada no artigo
    a = abs(v)
    return "muito forte" if a >= .8 else "forte" if a >= .6 else "moderada" if a >= .4 else "fraca" if a >= .2 else "muito fraca"


print("=== 1. Correlação de Spearman entre métodos (média dos grupos) ===")
mats = [g[METODOS].rank().corr() for _, g in r.groupby("grupo_lado")]
print((sum(mats) / len(mats)).round(2).to_string())

print("\n=== 2. Modelo principal x saldo de xG (Spearman), grupos de ataque ===")
linhas = []
for g, x in r[r.grupo_lado.isin(ATAQUE)].groupby("grupo_lado"):
    linhas.append({"grupo": g,
                   "restrito x gols-xG": x.restrito.corr(x.gols_menos_xg_p90, method="spearman"),
                   "restrito x assist-xA": x.restrito.corr(x.assist_menos_xa_p90, method="spearman")})
print(pd.DataFrame(linhas).round(2).to_string(index=False))
a = r[r.grupo_lado.isin(ATAQUE)]
top_xg = a.nlargest(15, "gols_menos_xg_p90")
print(f"Dos 15 maiores gols-xG/90 do ataque, {int(top_xg.eficiente.sum())} são eficientes no restrito e {int(top_xg.eficiente_ccr.sum())} no CCR livre; "
      f"posição mediana deles no ranking restrito: {int(top_xg.rank_restrito.median())}")

print("\n=== 3. H1 (valor de mercado) e H2 (idade) x modelo principal ===")
linhas = []
for g, x in r.groupby("grupo_lado"):
    pv = x.restrito.corr(x.valor_mercado_eur)
    pi = x.restrito.corr(x.idade)
    linhas.append({"grupo": g, "n": len(x), "H1 Pearson": pv, "H1 classe": classe(pv),
                   "H1 Spearman": x.restrito.corr(x.valor_mercado_eur, method="spearman"),
                   "H2 Pearson": pi, "H2 classe": classe(pi)})
t = pd.DataFrame(linhas)
print(t.round(2).to_string(index=False))
print(f"Todos juntos: H1 r = {r.restrito.corr(r.valor_mercado_eur):.2f}, H2 r = {r.restrito.corr(r.idade):.2f}")
r["faixa_idade"] = pd.cut(r.idade, [0, 23, 27, 31, 50], labels=["até 23", "24-27", "28-31", "32+"])
print(r.groupby("faixa_idade", observed=True).agg(n=("ccr", "size"), pct_eficientes=("eficiente", "mean"),
                                                   nota_media=("restrito", "mean")).round(2).to_string())

print("\n=== 4. Clubes ===")
tabela = []
for liga, div in [(268, "Série A"), (8814, "Série B")]:
    d = json.load(gzip.open(f"{LIGAS}/{liga}/2026.json.gz", "rt", encoding="utf-8"))
    for t_ in d["table"][0]["data"]["table"]["all"]:
        tabela.append({"time_id": t_["id"], "posicao": t_["idx"], "pts": t_["pts"], "jogos_tab": t_["played"]})
tabela = pd.DataFrame(tabela)
tabela["pts_por_jogo"] = tabela.pts / tabela.jogos_tab
ids = pd.read_csv(f"{BASE}/clubes_40.csv")[["time_id", "time"]]
cl = (r.merge(ids, on="time")
      .groupby(["time_id", "time", "divisao_2026"])
      .agg(avaliados=("ccr", "size"), eficientes=("eficiente", "sum"), nota_media=("restrito", "mean"),
           valor_elenco=("valor_elenco_clube_eur", "first"))
      .reset_index().merge(tabela, on="time_id"))
cl["pct_eficientes"] = cl.eficientes / cl.avaliados
for col in ["eficientes", "pct_eficientes", "nota_media"]:
    print(f"{col:15s} x pts/jogo: r = {cl[col].corr(cl.pts_por_jogo):+.2f} | x valor do elenco (Spearman): "
          f"{cl[col].corr(cl.valor_elenco, method='spearman'):+.2f}")
for div, x in cl.groupby("divisao_2026"):
    print(f"{div}: eficientes x pts/jogo r = {x.eficientes.corr(x.pts_por_jogo):+.2f}; "
          f"nota média x pts/jogo r = {x.nota_media.corr(x.pts_por_jogo):+.2f}")
print(r.groupby("divisao_2026").agg(n=("ccr", "size"), pct_eficientes=("eficiente", "mean"),
                                     nota_media=("restrito", "mean")).round(2).to_string())
print(cl.sort_values(["eficientes", "pct_eficientes"], ascending=False)
      [["time", "divisao_2026", "posicao", "pts", "avaliados", "eficientes", "pct_eficientes", "valor_elenco"]]
      .head(10).assign(valor_elenco=lambda x: (x.valor_elenco / 1e6).round(0), pct_eficientes=lambda x: x.pct_eficientes.round(2))
      .to_string(index=False))
cl.to_csv(f"{BASE}/clubes_eficiencia_2026.csv", index=False)

print("\n=== 5. Oportunidades: eficientes e baratos, top 3 por grupo (desempate pela cruzada) ===")
op = []
for g, x in r.groupby("grupo_lado"):
    barato = x[x.eficiente & (x.valor_mercado_eur < x.valor_mercado_eur.median())]
    op.append(barato.nlargest(3, "cruzada"))
op = pd.concat(op)
print(op[["grupo_lado", "nome", "time", "divisao_2026", "idade", "valor_mercado_eur", "cruzada", "rank_cruzada"]]
      .assign(valor_mercado_eur=lambda x: (x.valor_mercado_eur / 1e6).round(2), cruzada=lambda x: x.cruzada.round(3))
      .to_string(index=False))
op.to_csv(f"{BASE}/oportunidades_2026.csv", index=False)

"""Sensibilidade ao corte de minutos: repete o 03 com outros mínimos e compara as conclusões.

O script chama "03_rodar_dea.py <base> log <minutos>" para cada corte.
"""
import gzip
import json
import os
import subprocess
import sys

import pandas as pd

BASE = sys.argv[1] if len(sys.argv) > 1 else "../../dados-fotmob/consolidado/br40"
LIGAS = "../../dados-fotmob/ligas"
CORTES = [600, 1200, 1500]
ATAQUE = ["Atacante", "Ponta E", "Ponta D", "Meia atacante"]

pontos = {}
for liga in (268, 8814):
    d = json.load(gzip.open(f"{LIGAS}/{liga}/2026.json.gz", "rt", encoding="utf-8"))
    for t in d["table"][0]["data"]["table"]["all"]:
        pontos[t["id"]] = t["pts"] / t["played"]
ids = dict(pd.read_csv(f"{BASE}/clubes_40.csv")[["time", "time_id"]].values)

ref = pd.read_csv(f"{BASE}/resultados_dea_2026.csv")
rodadas = [("mediana (899)", ref)]
for corte in CORTES:
    arq = f"{BASE}/resultados_dea_2026_min{corte}.csv"
    subprocess.run([sys.executable, "03_rodar_dea.py", BASE, "log", str(corte)], check=True, stdout=subprocess.DEVNULL)
    rodadas.append((f"{corte} min", pd.read_csv(arq)))
rodadas.sort(key=lambda t: t[1].minutos.min())

linhas = []
for nome, r in rodadas:
    cl = r.groupby("time").agg(nota=("restrito", "mean"), n_ef=("eficiente", "sum"))
    cl["pts"] = [pontos[ids[t]] for t in cl.index]
    m = r.merge(ref[["jogador_id", "restrito", "eficiente"]], on="jogador_id", suffixes=("", "_ref"))
    baratos = lambda z: set(z[z.eficiente & (z.valor_mercado_eur < z.groupby("grupo_lado").valor_mercado_eur.transform("median"))].jogador_id)
    comuns = set(m.jogador_id)
    op_ref = baratos(ref) & comuns
    ficam = m[m.eficiente_ref]
    linhas.append({
        "corte": nome, "jogadores": len(r), "menor grupo": int(r.grupo_lado.value_counts().min()),
        "% eficientes": round(100 * r.eficiente.mean(), 1), "% CCR livre": round(100 * r.eficiente_ccr.mean(), 1),
        "Série A %": round(100 * r[r.divisao_2026 == "Série A"].eficiente.mean(), 1),
        "Série B %": round(100 * r[r.divisao_2026 == "Série B"].eficiente.mean(), 1),
        "nota clube x pts": round(cl.nota.corr(cl.pts), 2), "n efic x pts": round(cl.n_ef.corr(cl.pts), 2),
        "H1 valor": round(r.restrito.corr(r.valor_mercado_eur), 2), "H2 idade": round(r.restrito.corr(r.idade), 2),
        "ordem vs principal": round(m.groupby("grupo_lado")[["restrito", "restrito_ref"]]
                                    .apply(lambda g: g.restrito.corr(g.restrito_ref, method="spearman")).mean(), 2),
        "eficientes mantidos": f"{int(ficam.eficiente.sum())}/{len(ficam)}",
        "baratos mantidos": f"{len(baratos(r) & op_ref)}/{len(op_ref)}",
        "xG ataque (mín-máx)": "{:.2f}-{:.2f}".format(*(lambda s: (s.min(), s.max()))(
            pd.Series([g.restrito.corr(g.gols_menos_xg_p90, method="spearman")
                       for k, g in r.groupby("grupo_lado") if k in ("Atacante", "Ponta E", "Ponta D")]))),
    })
t = pd.DataFrame(linhas).set_index("corte")
print(t.T.to_string())
t.to_csv(f"{BASE}/sensibilidade_minutos.csv")

op = pd.read_csv(f"{BASE}/oportunidades_2026.csv")
print("\nNomes da lista de oportunidades que continuam eficientes em cada corte:")
for nome, r in rodadas:
    ef = set(r[r.eficiente].nome)
    presentes = set(r.nome)
    print(f"  {nome}: {sum(n in ef for n in op.nome)} de {sum(n in presentes for n in op.nome)} presentes"
          f" | deixam de ser eficientes: {', '.join(n for n in op.nome if n in presentes and n not in ef) or '-'}")

"""Corta, por posição, outputs redundantes: pares com |r| >= LIMITE (Pearson, taxas por 90, lados juntos).

Gols, assistências e grandes chances criadas são protegidos. Em cada par sai a variável não protegida
com maior correlação média com as demais; repete até não sobrar par acima do limite.
Grava cortes.json, lido por criterios.py.
"""
import json
import pandas as pd
import criterios as c

LIMITE = 0.60  # a partir de "forte" na tabela adotada no artigo de 2018
PROTEGIDAS = {"goals", "assists", "big_chance_created_team_title"}

b = pd.read_csv("../../dados-fotmob/consolidado/br40/base_analise_2026.csv")
a = b[b.acima_mediana]
cortes = {}
for pos in ["Atacante", "Ponta", "Meia atacante", "Volante", "Lateral", "Zagueiro", "Goleiro"]:
    chave = pos if pos in c.OUTPUTS_COMPLETOS else pos + (" E" if pos != "Zagueiro" else " D")
    x = a[a.grupo.str.replace(r" [ED]$", "", regex=True) == pos]
    cols = [k for k, _ in c.OUTPUTS_COMPLETOS[chave]]
    r = x[[k + "_p90" for k in cols]].fillna(0).corr().abs()
    r.index = r.columns = cols
    cortes[pos] = []
    while True:
        pares = [(r.loc[i, j], i, j) for n, i in enumerate(r.index) for j in r.columns[n + 1:]
                 if r.loc[i, j] >= LIMITE and not {i, j} <= PROTEGIDAS]
        if not pares:
            break
        v, i, j = max(pares)
        sai = max([k for k in (i, j) if k not in PROTEGIDAS], key=lambda k: r[k].mean())
        cortes[pos].append([sai, j if sai == i else i, round(float(v), 2)])
        r = r.drop(index=sai, columns=sai)
    print(f"{pos} ({len(x)}): {len(cols)} -> {len(r)} | " + ", ".join(f"{s} (com {k}, {v})" for s, k, v in cortes[pos]))
json.dump(cortes, open("cortes.json", "w"), indent=1)

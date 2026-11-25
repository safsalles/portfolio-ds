"""Explica quem é eficiente e por quê.

1. Quanto cada eficiente passa da fronteira: supereficiência com os mesmos pesos do modelo principal
   (a fronteira é recalculada sem o próprio jogador; acima de 1,00 = além do que os outros alcançam).
2. Critério decisivo: refaz a conta sem uma categoria por vez (pesos das demais renormalizados). A
   categoria cuja retirada mais derruba a nota é a decisiva; abaixo de 1,00 o jogador deixa de ser
   eficiente. Usa a nota, que é única, e não os pesos escolhidos pelo modelo, que podem não ser.
3. Árvores de decisão por posição: um resumo aproximado de quais estatísticas separam eficientes de não
   eficientes. Não é o modelo; o acerto é medido deixando um jogador de fora por vez.
"""
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.tree import DecisionTreeClassifier, plot_tree

import ahp
import criterios as c
import dea

AQUI = Path(__file__).parent
codigo = (AQUI / "03_rodar_dea.py").read_text(encoding="utf-8").split("b = pd.read_csv")[0]
ns = {}
exec(codigo, ns)  # reaproveita o preparo das variáveis do 03
outputs_dea, taxa = ns["outputs_dea"], ns["taxa"]

BASE = sys.argv[1] if len(sys.argv) > 1 else "../../dados-fotmob/consolidado/br40"
FIG = AQUI / "figuras"
FUNDO, TINTA, TINTA2, GRADE, AZUL = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6"
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
                     "figure.facecolor": FUNDO, "axes.facecolor": FUNDO, "savefig.facecolor": FUNDO,
                     "text.color": TINTA, "xtick.color": TINTA2, "axes.edgecolor": GRADE})
NOMES = {"goals": "Gols", "assists": "Assistências", "big_chance_created_team_title": "Grandes chances criadas",
         "chances_created": "Chances criadas", "recoveries": "Recuperações", "matchstats.headers.tackles": "Desarmes",
         "interceptions": "Interceptações", "dispossessed": "Perdas de posse", "Offsides": "Impedimentos",
         "big_chance_missed_title": "Grandes chances perdidas", "fouls": "Faltas", "dribbled_past": "Dribles sofridos",
         "dribbles_succeeded": "Dribles certos", "accurate_crosses": "Cruzamentos certos",
         "line_breaking_passes": "Passes que quebram linha", "was_fouled": "Faltas sofridas",
         "penalties_won": "Pênaltis sofridos", "accurate_passes": "Passes certos",
         "long_balls_accurate": "Passes longos certos", "aerials_won": "Duelos aéreos ganhos", "clearances": "Cortes",
         "shot_blocks": "Bloqueios", "saves": "Defesas", "goals_prevented": "Gols evitados",
         "keeper_high_claim": "Bolas altas", "keeper_sweeper": "Saídas do gol", "punches": "Socos"}
ORDEM = ["Atacante", "Ponta", "Meia atacante", "Volante", "Lateral", "Zagueiro", "Goleiro"]


def arquivo(s):
    return re.sub(r"\W+", "_", s.lower().replace("á", "a").replace("ê", "e"))


r = pd.read_csv(f"{BASE}/resultados_dea_2026.csv")
b = pd.read_csv(f"{BASE}/base_analise_2026.csv")
a = b[b.acima_mediana & b.grupo.notna()].copy()

linhas = []
for g, x in a.groupby("grupo_lado"):
    x = x.reset_index(drop=True)
    pos = x.grupo[0].removesuffix(" E").removesuffix(" D")
    x = x.assign(xg_mais_xa=x.expected_goals.fillna(0) + x.expected_assists.fillna(0),
                 log_valor_clube=np.log10(x.valor_elenco_clube_eur))
    extras = c.INPUTS_ATAQUE if g in c.GRUPOS_ATAQUE else []
    X = x[["minutos", "log_valor_clube"] + extras].fillna(0).to_numpy(float).copy()
    X[X <= 0] = 0.01
    Y = outputs_dea(x, c.OUTPUTS[g])
    cats = ahp.grupos(pos, list(Y.columns))
    nomes_cat = list(ahp.CATEGORIAS[pos])
    nota = dea.ccr_restrito(X, Y.to_numpy(), cats)[0]
    ef = np.flatnonzero(nota >= 1 - 1e-4)
    sup = dea.supereficiencia_restrita(X, Y.to_numpy(), cats, ef)
    sem = {}
    for i, nome in enumerate(nomes_cat):
        resto = [j for j in range(len(cats)) if j != i]
        cols = [k for j in resto for k in cats[j][0]]
        total = sum(cats[j][1] for j in resto)
        novos, p = [], 0
        for j in resto:
            n = len(cats[j][0])
            novos.append((list(range(p, p + n)), cats[j][1] / total))
            p += n
        sem[nome] = dea.supereficiencia_restrita(X, Y.to_numpy()[:, cols], novos, ef)
    for n_, k in enumerate(ef):
        queda = {nome: sup[n_] - sem[nome][n_] for nome in nomes_cat}
        decisivo = max(queda, key=queda.get)
        perde = [nome for nome in nomes_cat if sem[nome][n_] < 1 - 1e-4]
        linhas.append({"jogador_id": x.jogador_id[k], "nome": x.nome[k], "time": x.time[k], "grupo_lado": g,
                       "posicao": pos, "acima_da_fronteira": sup[n_],
                       "decisivo": decisivo if queda[decisivo] > 1e-4 else "nenhum sozinho",
                       "queda": queda[decisivo], "deixa_de_ser_sem": "; ".join(perde),
                       **{f"sem {nome}": sem[nome][n_] for nome in nomes_cat}})
d = pd.DataFrame(linhas)
assert len(d) == int(r.eficiente.sum()), (len(d), r.eficiente.sum())
assert (d.acima_da_fronteira >= 1 - 1e-4).all()
d.to_csv(f"{BASE}/criterio_decisivo.csv", index=False)

print("=== eficientes que deixam de ser eficientes sem cada categoria")
for pos in ORDEM:
    z = d[d.posicao == pos]
    cont = {k: int(z.deixa_de_ser_sem.fillna("").str.split("; ").apply(lambda v: k in v).sum()) for k in ahp.CATEGORIAS[pos]}
    print(f"{pos} ({len(z)}): {dict(sorted(cont.items(), key=lambda t: -t[1]))} | decisivo: {z.decisivo.value_counts().to_dict()}")

# gráficos: quanto cada eficiente passa da fronteira, com o critério decisivo
TETO = 2.0
for pos in ORDEM:
    z = d[d.posicao == pos]
    lados = sorted(z.grupo_lado.unique())
    alturas = [max((z.grupo_lado == l).sum(), 1) for l in lados]
    altura = 1.6 + 0.34 * sum(alturas) + 0.5 * len(lados)
    fig, eixos = plt.subplots(len(lados), 1, figsize=(10, altura), squeeze=False,
                              gridspec_kw={"height_ratios": [n + 0.6 for n in alturas]})
    for ax, lado in zip(eixos[:, 0], lados):
        t = z[z.grupo_lado == lado].sort_values("acima_da_fronteira")
        y = np.arange(len(t))
        v = np.minimum(t.acima_da_fronteira, TETO)
        ax.hlines(y, 1, v, color=GRADE, linewidth=3)
        ax.scatter(v, y, s=55, color=AZUL, zorder=3)
        ax.axvline(1, color=TINTA2, linewidth=1)
        for i, (_, j) in enumerate(t.iterrows()):
            valor = f"{j.acima_da_fronteira:.2f}".replace(".", ",") if np.isfinite(j.acima_da_fronteira) else "sem par"
            ax.annotate(valor, (v.iloc[i], i), xytext=(8, 0), textcoords="offset points", va="center", fontsize=9)
            marca = "" if j.decisivo in str(j.deixa_de_ser_sem).split("; ") else " (segue eficiente sem ele)"
            ax.text(TETO + 0.18, i, j.decisivo + marca, va="center", fontsize=9, color=TINTA2)
        ax.set_yticks(y, [f"{n} ({t_})" for n, t_ in zip(t.nome, t.time)], fontsize=9)
        ax.set_xlim(0.97, TETO + 0.85)
        ax.set_ylim(-0.7, len(t) - 0.3)
        ax.set_xticks([1, 1.25, 1.5, 1.75, 2], ["1,00", "1,25", "1,50", "1,75", "2,00"])
        ax.text(TETO + 0.18, len(t) - 0.35, "Critério decisivo", fontsize=9, fontweight="bold", va="bottom")
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="y", length=0)
        if len(lados) > 1:
            ax.set_title(lado, loc="left", fontsize=10, fontweight="bold")
    fig.text(0.01, 1 - 0.12 / altura, f"{pos}: eficientes e quanto passam da fronteira", fontsize=13,
             fontweight="bold", va="top")
    fig.text(0.01, 1 - 0.45 / altura, "1,00 é a fronteira formada pelos demais jogadores do mesmo grupo",
             color=TINTA2, va="top")
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.7 / altura))
    fig.savefig(FIG / f"fronteira_{arquivo(pos)}.png", dpi=150)
    plt.close(fig)

# árvores de decisão (lados juntos para ter mais casos)
print("\n=== árvores")
resumo = []
for pos in ORDEM:
    grupos = [g for g in c.OUTPUTS if g.removesuffix(" E").removesuffix(" D") == pos]
    x = a[a.grupo == pos] if pos in set(a.grupo) else a[a.grupo.isin(grupos)]
    x = x.reset_index(drop=True)
    saidas = c.OUTPUTS[grupos[0]]
    T = pd.DataFrame({NOMES[col] + " por 90": taxa(x, col) for col, _ in saidas})
    T["Minutos"] = x.minutos
    T["Valor do elenco (milhões €)"] = x.valor_elenco_clube_eur / 1e6
    if grupos[0] in c.GRUPOS_ATAQUE:
        T["xG + xA por 90"] = taxa(x, "expected_goals") + taxa(x, "expected_assists")
    alvo = x.jogador_id.isin(d.jogador_id).to_numpy()
    arv = DecisionTreeClassifier(max_depth=3, min_samples_leaf=5, class_weight="balanced", random_state=0)
    prev = cross_val_predict(arv, T, alvo, cv=LeaveOneOut())
    acerto = balanced_accuracy_score(alvo, prev)
    achados = int((prev & alvo).sum())
    arv.fit(T, alvo)
    dito = arv.predict(T)
    descreve, acerta_fora = float((dito == alvo).mean()), float((prev == alvo).mean())
    usadas = [T.columns[i] for i in dict.fromkeys(arv.tree_.feature) if i >= 0]
    resumo.append({"posicao": pos, "n": len(x), "eficientes": int(alvo.sum()), "acerto_balanceado": round(acerto, 2),
                   "descreve": descreve, "acerta_fora": acerta_fora, "achados_na_arvore": int((dito & alvo).sum()),
                   "eficientes_achados": achados, "alarmes_falsos": int((prev & ~alvo).sum()),
                   "primeira_pergunta": usadas[0] if usadas else "-"})
    fig, ax = plt.subplots(figsize=(15, 7.5))
    caixas = plot_tree(arv, feature_names=list(T.columns), ax=ax, impurity=False, filled=False, fontsize=9,
                       precision=2, label="none")
    t_ = arv.tree_
    for caixa in caixas:
        txt = caixa.get_text()
        if not txt.strip() or txt.strip() in ("True", "False", "  False", "True  "):
            caixa.set_text(txt.replace("True", "sim").replace("False", "não"))
    nos = [k for k in caixas if "[" in k.get_text()]
    for no, caixa in zip(range(t_.node_count), nos):
        folha = t_.children_left[no] == -1
        dentro = x.index[arv.decision_path(T).toarray()[:, no].astype(bool)]
        ne = int(alvo[dentro].sum())
        cab = "" if folha else f"{T.columns[t_.feature[no]]} até {t_.threshold[no]:.2f}?\n".replace(".", ",")
        caixa.set_text(f"{cab}{ne} eficientes de {len(dentro)}")
        azul = folha and bool(arv.classes_[t_.value[no][0].argmax()])
        caixa.get_bbox_patch().set_facecolor("#d6e6f8" if azul else FUNDO)
        caixa.get_bbox_patch().set_edgecolor(TINTA2)
    fig.text(0.01, 0.98, f"{pos}: o que separa os eficientes (resumo aproximado)", fontsize=13, fontweight="bold", va="top")
    fig.text(0.01, 0.942, f"Esta árvore descreve corretamente {descreve:.0%} dos {len(x)} jogadores e inclui "
             f"{int((dito & alvo).sum())} dos {int(alvo.sum())} eficientes nos grupos azuis. Em jogadores que ela não "
             f"viu: {acerta_fora:.0%} de acerto e {achados} dos {int(alvo.sum())} eficientes.", color=TINTA, va="top")
    fig.text(0.01, 0.908, f"Para comparar: dizer que ninguém é eficiente acertaria {1 - alvo.mean():.0%}. "
             "Esquerda = sim, direita = não. Azul = a árvore classifica o grupo como eficiente.",
             color=TINTA2, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(FIG / f"arvore_{arquivo(pos)}.png", dpi=130)
    plt.close(fig)
res = pd.DataFrame(resumo)
res.to_csv(f"{BASE}/arvores_resumo.csv", index=False)
print(res.to_string(index=False))

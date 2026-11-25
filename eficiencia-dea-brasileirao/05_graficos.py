"""Gera os gráficos do README em figuras/, a partir dos resultados do 03 e do 04."""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = sys.argv[1] if len(sys.argv) > 1 else "../../dados-fotmob/consolidado/br40"
SAIDA = Path(__file__).parent / "figuras"
SAIDA.mkdir(exist_ok=True)

FUNDO, TINTA, TINTA2, GRADE = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
AZUL, LARANJA, CINZA = "#2a78d6", "#eb6834", "#b4b2a9"
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
    "figure.facecolor": FUNDO, "axes.facecolor": FUNDO, "savefig.facecolor": FUNDO,
    "text.color": TINTA, "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "axes.edgecolor": GRADE, "axes.grid": True, "grid.color": GRADE, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True, "legend.frameon": False,
})

r = pd.read_csv(f"{BASE}/resultados_dea_2026.csv")
clubes = pd.read_csv(f"{BASE}/clubes_eficiencia_2026.csv")


def titulo(fig, t, sub):
    fig.text(0.01, 0.99, t, ha="left", va="top", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.99 - 0.30 / fig.get_figheight(), sub, ha="left", va="top", fontsize=10, color=TINTA2)


def salvar(fig, nome):
    fig.savefig(SAIDA / nome, dpi=160)
    plt.close(fig)
    print(nome)


# 1. eficientes por posição: CCR livre x modelo principal
t = r.groupby("grupo_lado")[["eficiente_ccr", "eficiente"]].mean().sort_values("eficiente")
fig, ax = plt.subplots(figsize=(8, 5.2))
y = range(len(t))
ax.hlines(y, t.eficiente, t.eficiente_ccr, color=GRADE, linewidth=3)
ax.scatter(t.eficiente_ccr, y, s=70, color=LARANJA, label="CCR livre (como em 2018)", zorder=3)
ax.scatter(t.eficiente, y, s=70, color=AZUL, label="Com pesos do AHP (principal)", zorder=3)
for i, (livre, pesos) in enumerate(zip(t.eficiente_ccr, t.eficiente)):
    ax.annotate(f"{pesos:.0%}", (pesos, i), xytext=(-9, 0), textcoords="offset points", ha="right", va="center")
    ax.annotate(f"{livre:.0%}", (livre, i), xytext=(9, 0), textcoords="offset points", ha="left", va="center")
ax.set_yticks(list(y), t.index)
ax.set_xlim(-0.06, 0.82)
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}" if v >= 0 else "")
ax.grid(axis="y", visible=False)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
titulo(fig, "Os pesos reduzem os eficientes de "
       f"{r.eficiente_ccr.mean():.1%} para {r.eficiente.mean():.1%}".replace(".", ","),
       "Percentual de jogadores eficientes em cada posição")
fig.tight_layout(rect=(0, 0, 1, 0.9))
salvar(fig, "eficientes_por_posicao.png")

# 2. clubes: nota média x pontos por jogo
fig, ax = plt.subplots(figsize=(8, 5.6))
for div, cor in [("Série A", AZUL), ("Série B", LARANJA)]:
    d = clubes[clubes.divisao_2026 == div]
    ax.scatter(d.nota_media, d.pts_por_jogo, s=60, color=cor, edgecolor=FUNDO, linewidth=1.5, label=div, zorder=3)
marcar = pd.concat([clubes.nlargest(3, "pts_por_jogo"), clubes.nsmallest(2, "pts_por_jogo"),
                    clubes.nlargest(2, "nota_media"), clubes.nsmallest(2, "nota_media"),
                    clubes[clubes.time == "Vasco da Gama"]]).drop_duplicates("time")
for _, c in marcar.iterrows():
    direita = c.nota_media < clubes.nota_media.quantile(0.85)
    baixo = c.time == "Vasco da Gama"  # evita encostar no ponto vizinho
    ax.annotate(c.time, (c.nota_media, c.pts_por_jogo), xytext=(0, -13) if baixo else (6 if direita else -6, 3),
                textcoords="offset points", ha="center" if baixo else "left" if direita else "right", fontsize=9,
                color=TINTA2)
rho = clubes.nota_media.corr(clubes.pts_por_jogo)
ax.set_xlabel("Nota média de eficiência dos jogadores avaliados")
ax.set_ylabel("Pontos por jogo na liga")
ax.legend(loc="upper left")
titulo(fig, "Clubes que pontuam mais tendem a ter notas médias maiores",
       f"Os 40 clubes das Séries A e B de 2026, correlação de Pearson {rho:.2f}".replace(".", ","))
fig.tight_layout(rect=(0, 0, 1, 0.9))
salvar(fig, "clubes_nota_pontos.png")

# 3. só xG x modelo, ataque
grupos = ["Atacante", "Ponta E", "Ponta D", "Meia atacante"]
fig, eixos = plt.subplots(2, 2, figsize=(8, 6.8), sharex=True, sharey=True)
for ax, g in zip(eixos.flat, grupos):
    x = r[r.grupo_lado == g]
    for ef, cor, rot in [(False, CINZA, "Não eficiente"), (True, AZUL, "Eficiente")]:
        d = x[x.eficiente == ef]
        ax.scatter(d.gols_menos_xg_p90, d.restrito, s=34, color=cor, edgecolor=FUNDO, linewidth=1, label=rot, zorder=3)
    rho = x.restrito.corr(x.gols_menos_xg_p90, method="spearman")
    ax.set_title(f"{g} (Spearman {rho:.2f})".replace(".", ",", 1), fontsize=10, loc="left")
    ax.axvline(0, color=TINTA2, linewidth=0.8)
fig.supxlabel("Gols menos xG, por 90 minutos", fontsize=10, color=TINTA2)
fig.supylabel("Nota no modelo principal", fontsize=10, color=TINTA2)
h, rotulos = eixos.flat[0].get_legend_handles_labels()
fig.legend(h, rotulos, loc="upper right", bbox_to_anchor=(0.99, 0.925), ncol=2)
titulo(fig, "Finalizar acima do esperado conta muito, menos no meia atacante",
       "Cada ponto é um jogador")
fig.tight_layout(rect=(0, 0, 1, 0.89))
salvar(fig, "dea_vs_xg.png")

# 4. oportunidades: valor de mercado x nota, todos os jogadores
d = r.dropna(subset=["valor_mercado_eur"])
fig, ax = plt.subplots(figsize=(8, 5.2))
for ef, cor, rot in [(False, CINZA, "Não eficiente"), (True, AZUL, "Eficiente")]:
    z = d[d.eficiente == ef]
    ax.scatter(z.valor_mercado_eur / 1e6, z.restrito, s=26, color=cor, edgecolor=FUNDO, linewidth=0.8, label=rot, zorder=3)
ax.set_xscale("log")
ax.set_xticks([0.1, 0.3, 1, 3, 10, 30], ["0,1", "0,3", "1", "3", "10", "30"])
ax.set_xlabel("Valor de mercado do jogador, em milhões de euros (escala log)")
ax.set_ylabel("Nota no modelo principal")
ax.legend(loc="lower right")
rho = d.restrito.corr(d.valor_mercado_eur)
titulo(fig, "Preço quase não indica eficiência",
       f"{len(d)} jogadores, correlação de Pearson {rho:.2f}".replace(".", ","))
fig.tight_layout(rect=(0, 0, 1, 0.9))
salvar(fig, "valor_vs_eficiencia.png")

"""Gráfico de radar para comparar conjuntos critério a critério."""

import sys

import numpy as np

COLORS = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"


def interactive():
    """Só abre a janela do gráfico quando alguém está usando o programa no terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def plot_radar(labels, panels, path=None, show=False, note=""):
    """Desenha um radar por painel, com um eixo por critério.

    `labels` são os nomes dos eixos, já prontos para mostrar. `panels` é uma lista de
    (título, perfis), e cada perfil é (rótulo, valores, cor, estilo). O estilo "fill"
    preenche a área, "dash" desenha a linha tracejada e "line" a linha cheia. Salva o
    gráfico em `path`, se houver, e abre uma janela com ele se `show` for verdadeiro.
    """
    import matplotlib

    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    closed = np.append(angles, angles[0])

    figure, axes = plt.subplots(
        1, len(panels), figsize=(6.4 * len(panels), 7.2), subplot_kw={"polar": True},
        facecolor=SURFACE,
    )
    for axis, (title, profiles) in zip(np.atleast_1d(axes), panels):
        axis.set_facecolor(SURFACE)
        axis.set_theta_offset(np.pi / 2)
        axis.set_theta_direction(-1)
        for name, values, color, style in profiles:
            ring = np.append(values, values[0])
            if style == "fill":
                axis.fill(closed, ring, color=color, alpha=0.18, linewidth=0)
            axis.plot(
                closed, ring, color=color, linewidth=2, label=name, clip_on=False,
                linestyle=(0, (4, 3)) if style == "dash" else "-",
            )
        # Com pesos por grupo, um valor pode passar de 1, então a escala vem dos dados.
        top = max(np.ceil(max(float(np.max(values)) for _, values, _, _ in profiles) * 2) / 2, 0.5)
        ticks = np.arange(0.5, top, 0.5)
        axis.set_ylim(0, top)
        axis.set_yticks(ticks)
        axis.set_yticklabels([f"{tick:g}".replace(".", ",") for tick in ticks], color=MUTED, fontsize=8)
        axis.set_rlabel_position(180 / len(labels))
        axis.set_xticks(angles)
        axis.set_xticklabels(list(labels), color=INK, fontsize=8)
        axis.tick_params(axis="x", pad=6)
        axis.grid(color=GRID, linewidth=0.8)
        axis.spines["polar"].set_color(GRID)
        axis.set_title(title, color=INK, fontsize=11, pad=34)
        axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False, fontsize=9)
    if note:
        figure.text(0.5, 0.02, note, ha="center", color=MUTED, fontsize=9)
    figure.subplots_adjust(left=0.07, right=0.93, top=0.82, bottom=0.17, wspace=0.55)
    if path:
        figure.savefig(path, dpi=130, facecolor=figure.get_facecolor())
    if show:
        plt.show()
    plt.close(figure)

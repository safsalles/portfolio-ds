"""MEM: escolhe o melhor conjunto de alternativas testando todas as combinações.

Para rodar: python mem.py

É o Método de Escolha Múltipla como a tese de da Hora descreve, sem algoritmo genético.
Os números das equações citadas abaixo são os da tese. O exemplo em data/ é fictício.
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from itertools import combinations
from math import comb, isfinite
from pathlib import Path

import numpy as np

DEFAULT_DATA_DIR = Path(__file__).parent / "data"
DEFAULT_CHOICES = 2
DEFAULT_TAU = 0.24
DEFAULT_TOP = 10
SENSITIVITY_STEP = 0.01
MAX_EVALUATIONS = 20_000_000  # acima disso, testar tudo já não é prático


@dataclass(frozen=True)
class Problem:
    alternatives: tuple
    criteria: tuple
    payment: np.ndarray  # matriz A
    direction: np.ndarray  # 1 quando mais é melhor e 0 quando mais é pior
    weights: np.ndarray  # vetor W
    complementarity: np.ndarray  # matriz C


@dataclass(frozen=True)
class Choice:
    position: int
    alternatives: tuple
    share: float  # fração das combinações de critérios que alcançam o tau


# ======================================================================================
# DADOS
# ======================================================================================

def _read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def load_problem(folder=DEFAULT_DATA_DIR):
    folder = Path(folder)
    criteria_rows = _read_rows(folder / "criteria.csv")
    criteria = tuple(row["criterion"] for row in criteria_rows)
    direction = np.array([int(row["direction"]) for row in criteria_rows])
    weights = np.array([float(row["weight"]) for row in criteria_rows])

    alternative_rows = _read_rows(folder / "alternatives.csv")
    alternatives = tuple(row["alternative"] for row in alternative_rows)
    payment = np.array(
        [[float(row[name]) for name in criteria] for row in alternative_rows]
    )

    matrix_rows = {row["criterion"]: row for row in _read_rows(folder / "complementarity.csv")}
    complementarity = np.zeros((len(criteria), len(criteria)))
    for i, first in enumerate(criteria):
        for j, second in enumerate(criteria):
            if i != j:
                complementarity[i, j] = float(matrix_rows[first][second])

    return Problem(alternatives, criteria, payment, direction, weights, complementarity)


# ======================================================================================
# MÉTODO
# ======================================================================================

def normalize(problem):
    """Equação 3.1: põe cada critério entre 0 e 1, com 1 para a melhor avaliação."""
    highest = problem.payment.max(axis=0)
    lowest = problem.payment.min(axis=0)
    flat = [name for name, top, low in zip(problem.criteria, highest, lowest) if top == low]
    if flat:
        raise ValueError(f"Critério com o mesmo valor em todas as alternativas: {flat[0]}.")
    best = np.where(problem.direction == 1, highest, lowest)
    worst = np.where(problem.direction == 1, lowest, highest)
    return (problem.payment - worst) / (best - worst)


def check_size(problem, choices):
    n_alternatives = len(problem.alternatives)
    n_criteria = len(problem.criteria)
    if not 2 <= choices <= min(n_alternatives, n_criteria):
        raise ValueError(
            f"A escolha precisa ter de 2 a {min(n_alternatives, n_criteria)} alternativas, "
            f"e veio {choices}."
        )
    total = comb(n_alternatives, choices) * comb(n_criteria, choices)
    if total > MAX_EVALUATIONS:
        raise ValueError(f"A matriz B teria {total} avaliações, demais para testar uma a uma.")


def criteria_factors(problem, choices):
    """Parte da Equação 3.4 que só depende dos critérios: média de W e c' (Equação 3.5)."""
    groups = list(combinations(range(len(problem.criteria)), choices))
    factors = []
    for group in groups:
        c_mean = np.mean([problem.complementarity[j, k] for j, k in combinations(group, 2)])
        factors.append(problem.weights[list(group)].mean() * c_mean)
    return np.array(groups), np.array(factors)


def matrix_b_prime(problem, choices):
    """Equação 3.4: uma linha por conjunto de alternativas, uma coluna por grupo de critérios."""
    normalized = normalize(problem)
    groups, factors = criteria_factors(problem, choices)
    sets = list(combinations(range(len(problem.alternatives)), choices))
    means = np.array([normalized[list(chosen)].mean(axis=0) for chosen in sets])
    return sets, means[:, groups].mean(axis=2) * factors


def rank(problem, choices, tau):
    """Equações 3.8 e 3.9: ordena os conjuntos pela fração que alcança o tau. Empates valem."""
    check_size(problem, choices)
    sets, values = matrix_b_prime(problem, choices)
    # O arredondamento evita que um valor igual ao tau caia abaixo dele por erro de ponto flutuante.
    shares = (values.round(12) >= tau).mean(axis=1)
    order = sorted(range(len(sets)), key=lambda row: (-shares[row], sets[row]))

    ranking = []
    for place, row in enumerate(order, start=1):
        tied = ranking and shares[row] == ranking[-1].share
        position = ranking[-1].position if tied else place
        names = tuple(problem.alternatives[i] for i in sets[row])
        ranking.append(Choice(position, names, float(shares[row])))
    return ranking


def individual_order(problem):
    """Ordena as alternativas pela média ponderada, a escolha comum sem o MEM."""
    scores = normalize(problem) @ problem.weights / problem.weights.sum()
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
    return [(problem.alternatives[i], float(scores[i])) for i in order]


# ======================================================================================
# GRÁFICO
# ======================================================================================

COLORS = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"


def interactive():
    """Só abre a janela do gráfico quando alguém está usando o programa no terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def plot_radar(problem, panels, path=None, show=False):
    """Desenha um radar por conjunto: cada alternativa em linha e a média do conjunto preenchida.

    `panels` é uma lista de (título, nomes das alternativas). A média é o que o MEM avalia.
    Salva o gráfico em `path`, se houver, e abre uma janela com ele se `show` for verdadeiro.
    """
    import matplotlib

    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    normalized = normalize(problem)
    angles = np.linspace(0, 2 * np.pi, len(problem.criteria), endpoint=False)
    closed = np.append(angles, angles[0])
    labels = [f"{name}*" if direction == 0 else name for name, direction in zip(problem.criteria, problem.direction)]

    figure, axes = plt.subplots(
        1, len(panels), figsize=(5.2 * len(panels), 6.4), subplot_kw={"polar": True},
        facecolor="#fcfcfb",
    )
    for axis, (title, names) in zip(np.atleast_1d(axes), panels):
        rows = [problem.alternatives.index(name) for name in names]
        mean = normalized[rows].mean(axis=0)
        axis.set_facecolor("#fcfcfb")
        axis.set_theta_offset(np.pi / 2)
        axis.set_theta_direction(-1)
        axis.set_rlabel_position(180 / len(problem.criteria))
        axis.fill(closed, np.append(mean, mean[0]), color=MUTED, alpha=0.25, linewidth=0)
        axis.plot(closed, np.append(mean, mean[0]), color=INK, linewidth=2, label="Média do conjunto")
        for row in rows:
            values = np.append(normalized[row], normalized[row][0])
            color = COLORS[row % len(COLORS)]
            axis.plot(closed, values, color=color, linewidth=2, label=problem.alternatives[row], clip_on=False)
            axis.plot(angles, normalized[row], "o", color=color, markersize=6, clip_on=False)
        axis.set_ylim(0, 1)
        axis.set_yticks([0.25, 0.5, 0.75, 1])
        axis.set_yticklabels(["", "0,5", "", "1"], color=MUTED, fontsize=8)
        axis.set_xticks(angles)
        axis.set_xticklabels(labels, color=INK, fontsize=9)
        axis.tick_params(axis="x", pad=10)
        axis.grid(color=GRID, linewidth=0.8)
        axis.spines["polar"].set_color(GRID)
        axis.set_title(title, color=INK, fontsize=11, pad=42)
        axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False, fontsize=9)
    if 0 in problem.direction:
        figure.text(0.5, 0.02, "* Menos é melhor, então o eixo está invertido: 1 é a melhor avaliação.",
                    ha="center", color=MUTED, fontsize=9)
    figure.subplots_adjust(left=0.06, right=0.94, top=0.80, bottom=0.16, wspace=0.45)
    if path:
        figure.savefig(path, dpi=150, facecolor=figure.get_facecolor())
    if show:
        plt.show()
    plt.close(figure)


def comparison_panels(problem, choices, tau):
    """Compara as melhores pela média ponderada com o 1.º lugar do MEM."""
    ranking = rank(problem, choices, tau)
    leaders = {name for name, _ in individual_order(problem)[:choices]}
    usual = next(choice for choice in ranking if set(choice.alternatives) == leaders)
    best = ranking[0] if ranking[0] != usual else None

    def title(name, choice):
        share = f"{choice.share:.1%}".replace(".", ",")
        return f"{name}: {label(choice.alternatives)}\n{choice.position}.º no MEM, {share} dos grupos"

    panels = [(title("Média ponderada", usual), usual.alternatives)]
    if best is not None:
        panels.append((title("MEM", best), best.alternatives))
    return panels


# ======================================================================================
# LINHA DE COMANDO
# ======================================================================================

def tau_argument(text):
    try:
        tau = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} não é um número") from None
    if not (isfinite(tau) and tau > 0):
        raise argparse.ArgumentTypeError("o tau precisa ser um número finito maior que 0")
    return tau


def build_parser():
    parser = argparse.ArgumentParser(description="Método de Escolha Múltipla, sem algoritmo genético")
    parser.add_argument("--choices", type=int, default=DEFAULT_CHOICES, help="alternativas a escolher")
    parser.add_argument("--tau", type=tau_argument, default=DEFAULT_TAU, help="tau de corte")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP, help="conjuntos mostrados")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_DIR, help="pasta dos dados")
    parser.add_argument("--radar", type=Path, help="salva o gráfico de radar neste arquivo (.png)")
    parser.add_argument("--no-plot", action="store_true", help="não abre a janela do gráfico no final")
    return parser


def label(names):
    return ", ".join(names)


def run(args):
    if args.top < 1:
        raise ValueError(f"A lista precisa mostrar pelo menos 1 conjunto, e veio {args.top}.")
    problem = load_problem(args.data)
    ranking = rank(problem, args.choices, args.tau)
    n_groups = comb(len(problem.criteria), args.choices)
    print(
        f"{len(problem.alternatives)} alternativas e {len(problem.criteria)} critérios, "
        f"escolhendo {args.choices}: {len(ranking)} conjuntos e {n_groups} grupos de critérios."
    )

    print(f"\nMelhores conjuntos (tau {args.tau}):")
    for choice in ranking[: args.top]:
        print(f"  {choice.position:>3}. {label(choice.alternatives):<20} {choice.share:6.1%}")

    leaders = {name for name, _ in individual_order(problem)[: args.choices]}
    usual = next(choice for choice in ranking if set(choice.alternatives) == leaders)
    print(
        f"\nAs {args.choices} melhores pela média ponderada são {label(usual.alternatives)}: "
        f"{usual.position}.º lugar no MEM, com {usual.share:.1%}."
    )

    print("\nSensibilidade do tau:")
    for tau in (args.tau - SENSITIVITY_STEP, args.tau + SENSITIVITY_STEP):
        if tau > 0:
            first = [c for c in rank(problem, args.choices, tau) if c.position == 1]
            sets = "; ".join(label(choice.alternatives) for choice in first)
            print(f"  tau {tau:.2f}: {sets} ({first[0].share:.1%})")

    show = interactive() and not args.no_plot
    if args.radar:
        print(f"\nGráfico de radar salvo em {args.radar}")
    if show:
        print("\nO gráfico de radar abriu em outra janela. Feche a janela para terminar.")
    if args.radar or show:
        plot_radar(problem, comparison_panels(problem, args.choices, args.tau), args.radar, show)


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        run(args)
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(f"Erro: {error}") from None


if __name__ == "__main__":
    main()

"""Exemplo pequeno: escolher 2 de 8 candidatos testando todas as combinações.

Para rodar: python exemplo.py

É o MEM como a tese de da Hora descreve, sem algoritmo genético. Os dados são fictícios e
seguem a ideia do problema de recrutamento da tese. Com `--regra minimo`, roda a adaptação
da dissertação nos mesmos dados.
"""

import argparse
import sys
from dataclasses import dataclass
from math import comb, isfinite
from pathlib import Path

import numpy as np

from mem.busca import MAX_EVALUATIONS, exhaustive
from mem.problema import load_problem as _load_problem
from mem.problema import normalize
from mem.radar import COLORS, MUTED, interactive, plot_radar
from mem.regras import build_rule

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_CHOICES = 2
DEFAULT_TAU = 0.24
DEFAULT_TOP = 10
SENSITIVITY_STEP = 0.01
RULES = ("media", "minimo")


@dataclass(frozen=True)
class Ranked:
    position: int
    alternatives: tuple[str, ...]
    share: float  # fração dos grupos de critérios que alcançam o tau


def load_problem(folder=DEFAULT_DATA_DIR):
    return _load_problem(folder)


def check_size(problem, choices, regra="media"):
    n_alternatives = len(problem.alternatives)
    n_criteria = len(problem.criteria)
    if not 2 <= choices <= min(n_alternatives, n_criteria):
        raise ValueError(
            f"A escolha precisa ter de 2 a {min(n_alternatives, n_criteria)} alternativas, "
            f"e veio {choices}."
        )
    per_set = comb(n_criteria, choices if regra == "media" else 2)
    total = comb(n_alternatives, choices) * per_set
    if total > MAX_EVALUATIONS:
        raise ValueError(f"A matriz B teria {total} avaliações, demais para testar uma a uma.")


def rank(problem, choices, tau, regra="media"):
    """Ordena todos os conjuntos pela fração dos grupos de critérios que alcança o tau."""
    check_size(problem, choices, regra)
    normalize(problem.values, problem.direction, allow_constant=False, criteria=problem.criteria)
    rule = build_rule(problem, regra, tau, size=choices)
    return [
        Ranked(c.position, tuple(problem.alternatives[i] for i in c.alternatives), c.score)
        for c in exhaustive(rule, len(problem.alternatives), choices)
    ]


def individual_order(problem):
    """Ordena as alternativas pela média ponderada, a escolha comum sem o MEM."""
    scores = normalize(problem.values, problem.direction) @ problem.weights / problem.weights.sum()
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
    return [(problem.alternatives[i], float(scores[i])) for i in order]


def label(names):
    return ", ".join(names)


def comparison_panels(problem, choices, tau, regra="media"):
    """Compara as melhores pela média ponderada com o 1.º lugar do MEM."""
    ranking = rank(problem, choices, tau, regra)
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


def draw(problem, panels, path=None, show=False):
    """Um radar por conjunto: cada alternativa em linha e a média do conjunto preenchida."""
    normalized = normalize(problem.values, problem.direction)
    profiles = []
    for title, names in panels:
        rows = [problem.alternatives.index(name) for name in names]
        lines = [("Média do conjunto", normalized[rows].mean(axis=0), MUTED, "fill")]
        lines += [(problem.alternatives[r], normalized[r], COLORS[r % len(COLORS)], "line") for r in rows]
        profiles.append((title, lines))
    labels = [f"{name}*" if d == 0 else name for name, d in zip(problem.criteria, problem.direction)]
    note = "* Menos é melhor, então o eixo está invertido: 1 é a melhor avaliação." if 0 in problem.direction else ""
    plot_radar(labels, profiles, path, show, note)


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
    parser = argparse.ArgumentParser(description="Método de Escolha Múltipla, testando todas as combinações")
    parser.add_argument("--choices", type=int, default=DEFAULT_CHOICES, help="alternativas a escolher")
    parser.add_argument("--tau", type=tau_argument, default=DEFAULT_TAU, help="tau de corte")
    parser.add_argument("--regra", choices=RULES, default="media", help="media (tese) ou minimo (adaptação)")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP, help="conjuntos mostrados")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_DIR, help="pasta dos dados")
    parser.add_argument("--radar", type=Path, help="salva o gráfico de radar neste arquivo (.png)")
    parser.add_argument("--no-plot", action="store_true", help="não abre a janela do gráfico no final")
    return parser


def run(args):
    if args.top < 1:
        raise ValueError(f"A lista precisa mostrar pelo menos 1 conjunto, e veio {args.top}.")
    problem = load_problem(args.data)
    ranking = rank(problem, args.choices, args.tau, args.regra)
    n_groups = comb(len(problem.criteria), args.choices if args.regra == "media" else 2)
    print(
        f"{len(problem.alternatives)} alternativas e {len(problem.criteria)} critérios, "
        f"escolhendo {args.choices}: {len(ranking)} conjuntos e {n_groups} grupos de critérios."
    )

    print(f"\nMelhores conjuntos (regra {args.regra}, tau {args.tau}):")
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
            first = [c for c in rank(problem, args.choices, tau, args.regra) if c.position == 1]
            sets = "; ".join(label(choice.alternatives) for choice in first)
            print(f"  tau {tau:.2f}: {sets} ({first[0].share:.1%})")

    show = interactive() and not args.no_plot
    if args.radar:
        print(f"\nGráfico de radar salvo em {args.radar}")
    if show:
        print("\nO gráfico de radar abriu em outra janela. Feche a janela para terminar.")
    if args.radar or show:
        draw(problem, comparison_panels(problem, args.choices, args.tau, args.regra), args.radar, show)


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        run(args)
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(f"Erro: {error}") from None


if __name__ == "__main__":
    main()

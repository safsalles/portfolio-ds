"""Exemplo grande: montar uma equipe de projeto com 4 de 300 candidatos.

Para rodar: python exemplo.py

São 2 analistas, 1 engenheiro e 1 gestor. Testar todas as equipes possíveis seria
inviável, então a busca é feita pelo algoritmo genético. O programa compara três equipes:
a da regra `media` (a da tese), a da regra `minimo` (a adaptação) e a escolha
tradicional, que pega os melhores de cada cargo sem olhar a complementação.
Os dados são fictícios e saem de gerar_dados.py.
"""

import argparse
import sys
from math import comb
from pathlib import Path

import numpy as np

from mem.busca import GAConfig, run_ga, traditional_choice
from mem.problema import load_problem as _load_problem
from mem.problema import normalize
from mem.radar import COLORS, MUTED, interactive, plot_radar
from mem.regras import build_rule

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_SEED = 2026
QUOTAS = {"analista": 2, "engenheiro": 1, "gestor": 1}
SIZE = sum(QUOTAS.values())
RULES = ("media", "minimo")

# Tau de cada regra neste exemplo. Com um tau baixo demais, quase toda equipe passa em
# todos os grupos de critérios, e a nota não separa ninguém; alto demais, ninguém passa.
# Para cada regra, testamos o tau de 0,01 a 1,00, de 0,01 em 0,01, e ficamos com o valor
# em que a escolha tradicional fica mais perto de 50% dos grupos (no empate, o menor
# tau). Assim sobra espaço para a busca mostrar se acha uma equipe melhor.
TAU = {"media": 0.63, "minimo": 0.54}


def load_problem(folder=DEFAULT_DATA_DIR):
    return _load_problem(folder)


def build_teams(problem, seed, config=None):
    """As três equipes: a de cada regra, achada pelo algoritmo genético, e a tradicional."""
    rules = {regra: build_rule(problem, regra, TAU[regra], size=SIZE) for regra in RULES}
    teams = {}
    for regra, rule in rules.items():
        result = run_ga(rule, problem.groups, QUOTAS, SIZE, config, seed=seed)
        teams[f"Regra {regra}"] = sorted(result.team)
    usual = traditional_choice(rules["media"].payment, SIZE, problem.groups, QUOTAS)
    teams["Escolha tradicional"] = sorted(usual)
    scores = {
        name: {regra: rule.rate(team)[0] for regra, rule in rules.items()}
        for name, team in teams.items()
    }
    return teams, scores


def member_label(problem, index):
    return f"{problem.alternatives[index]} ({problem.groups[index]})"


def draw(problem, teams, scores, path=None, show=False):
    """Um radar por equipe: cada pessoa em linha e a média da equipe preenchida."""
    normalized = normalize(problem.values, problem.direction)
    panels = []
    for name, team in teams.items():
        lines = [("Média da equipe", normalized[team].mean(axis=0), MUTED, "fill")]
        lines += [
            (member_label(problem, index), normalized[index], COLORS[k % len(COLORS)], "line")
            for k, index in enumerate(team)
        ]
        notes = ", ".join(f"{regra} {share:.0%}" for regra, share in scores[name].items())
        panels.append((f"{name}\n{notes}", lines))
    plot_radar(list(problem.criteria), panels, path, show)


# ======================================================================================
# LINHA DE COMANDO
# ======================================================================================

def build_parser():
    parser = argparse.ArgumentParser(description="Equipe de projeto com o MEM e o algoritmo genético")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="semente do algoritmo genético")
    parser.add_argument(
        "--iterations", type=int, default=GAConfig().iterations, help="iterações do algoritmo genético"
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_DIR, help="pasta dos dados")
    parser.add_argument("--radar", type=Path, help="salva o gráfico de radar neste arquivo (.png)")
    parser.add_argument("--no-plot", action="store_true", help="não abre a janela do gráfico no final")
    return parser


def run(args):
    problem = load_problem(args.data)
    vagas = ", ".join(f"{quota} {group}" for group, quota in QUOTAS.items())
    print(
        f"{len(problem.alternatives)} candidatos e {len(problem.criteria)} critérios. "
        f"Equipe de {SIZE}: {vagas}."
    )
    print(
        f"Regra media: {comb(len(problem.criteria), SIZE)} grupos de critérios (tau {TAU['media']}). "
        f"Regra minimo: {comb(len(problem.criteria), 2)} pares de critérios (tau {TAU['minimo']})."
    )

    teams, scores = build_teams(problem, args.seed, GAConfig(iterations=args.iterations))
    for name, team in teams.items():
        notes = " | ".join(f"nota {regra} {share:6.1%}" for regra, share in scores[name].items())
        print(f"\n{name}: {notes}")
        for index in team:
            print(f"  {member_label(problem, index)}")

    same = teams["Regra media"] == teams["Regra minimo"]
    print("\nAs duas regras escolheram a mesma equipe." if same else "\nAs duas regras escolheram equipes diferentes.")

    show = interactive() and not args.no_plot
    if args.radar:
        print(f"\nGráfico de radar salvo em {args.radar}")
    if show:
        print("\nO gráfico de radar abriu em outra janela. Feche a janela para terminar.")
    if args.radar or show:
        draw(problem, teams, scores, args.radar, show)


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        run(args)
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(f"Erro: {error}") from None


if __name__ == "__main__":
    main()

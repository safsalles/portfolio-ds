"""MEM-GA: monta um time de futebol com o Método de Escolha Múltipla e algoritmo genético.

Para rodar, a partir da pasta `football-analytics`: python -m escalacao

A nota e a busca vêm do pacote `mem` (regra `minimo` e algoritmo genético), com a posição
no papel de grupo e a formação como vagas por posição.
"""

import argparse
import secrets
import sys
from pathlib import Path

from comum.campo import pitch_lines, plot_radar
from comum.goleiros import GOALKEEPER_CRITERIA
from comum.jogadores import DEFAULT_DATA_DIR, DEFAULT_MIN_MINUTES, DEFAULT_TAU, build_scorer, load_dataset
from comum.terminal import finish_with_radar, tau_argument
from escalacao.formacoes import PRESETS, FormationError, parse_formation
from memga.busca import GAConfig, run_ga, traditional_choice
from memga.radar import COLORS, MUTED

PROGRESS_BAR_WIDTH = 30


def check_team_size(team_size, n_players):
    if team_size < 1:
        raise ValueError(f"O time precisa ter pelo menos 1 jogador, e veio {team_size}.")
    if team_size > n_players:
        raise ValueError(f"O time pede {team_size} jogadores, mas os dados têm só {n_players}.")


def strongest_team(dataset, quotas, team_size):
    """Os jogadores de maior desempenho somado, respeitando a formação quando ela existe."""
    return traditional_choice(dataset.payment, team_size, dataset.positions, quotas)


def team_radar(dataset, scorer, team, quotas, path=None, show=False):
    """Compara o time do MEM-GA com os mais fortes individualmente na mesma formação."""
    strongest = strongest_team(dataset, quotas, len(team))
    team = list(team)

    def score(players):
        return f"{scorer.rate(players)[0]:.4f}".replace(".", ",")

    plot_radar(dataset.criteria, [(
        f"Média do time por critério\nnota {score(team)} no MEM-GA e {score(strongest)} na escolha tradicional",
        [("Média da liga", scorer.payment.mean(axis=0), MUTED, "dash"),
         ("Escolha tradicional", scorer.payment[strongest].mean(axis=0), COLORS[1], "line"),
         ("MEM-GA", scorer.payment[team].mean(axis=0), COLORS[0], "fill")],
    )], path, show)


def build_parser():
    defaults = GAConfig()
    parser = argparse.ArgumentParser(
        prog="python -m escalacao",
        description="Monta um time com o Método de Escolha Múltipla e algoritmo genético.",
    )
    parser.add_argument("--formation", help="formação; se ficar de fora, o programa pergunta")
    parser.add_argument("--data", default=DEFAULT_DATA_DIR, help="pasta com os três arquivos CSV")
    parser.add_argument(
        "--min-minutes",
        type=int,
        default=DEFAULT_MIN_MINUTES,
        help="mínimo de minutos jogados para entrar na análise",
    )
    parser.add_argument("--team-size", type=int, default=10, help="jogadores de linha no time")
    parser.add_argument("--tau", type=tau_argument, default=DEFAULT_TAU, help="tau de corte do grupo")
    parser.add_argument("--seed", type=int, help="semente, para repetir um resultado")
    parser.add_argument("--radar", type=Path, help="salva o gráfico de radar neste arquivo (.png)")
    parser.add_argument("--no-plot", action="store_true", help="não abre a janela do gráfico no final")
    parser.add_argument("--iterations", type=int, default=defaults.iterations)
    parser.add_argument("--population", type=int, default=defaults.population)
    parser.add_argument(
        "--stagnation",
        type=int,
        default=defaults.stagnation,
        help="iterações sem melhora até a mutação",
    )
    parser.add_argument(
        "--mutations",
        type=int,
        default=defaults.mutation_attempts,
        help="tentativas em cada mutação",
    )
    return parser


def ask_formation(positions, team_size):
    print(f"Atalhos: {', '.join(PRESETS)}")
    print("Ou monte a sua: zag=3,le=1,ld=1,vol=3,mei=1,ata=1")
    print("Deixe em branco para o time livre, sem quotas por posição.")
    while True:
        try:
            return parse_formation(input("Qual formação você quer? "), positions, team_size)
        except FormationError as error:
            print(error)


def show_progress(iteration, total, score):
    filled = PROGRESS_BAR_WIDTH * iteration // total
    bar = "#" * filled + "-" * (PROGRESS_BAR_WIDTH - filled)
    print(f"\r  [{bar}] iteração {iteration}/{total} | melhor nota {score:.4f}", end="", flush=True)


def print_team(dataset, team):
    strengths = dataset.payment.sum(axis=1)
    for line in pitch_lines(dataset, strengths, team):
        print(f"  {line}")
    print()

    order = sorted(team, key=lambda player: -strengths[player])
    width = max(len(dataset.players[player]) for player in order)
    print(f"  {'Jogador':<{width}}  {'Pos':<4}  Desempenho somado")
    for player in order:
        print(
            f"  {dataset.players[player]:<{width}}  {dataset.positions[player]:<4}"
            f"  {strengths[player]:.4g} de {len(dataset.criteria)}"
        )
    if dataset.goalkeeper:
        keeper = dataset.goalkeeper
        print(
            f"\n  Goleiro: {keeper['name']}, {keeper['hits']} de {len(GOALKEEPER_CRITERIA)} critérios"
            f" ({keeper['save_rate']:.1%} de defesas, {keeper['long_pass_rate']:.1%} de passes"
            f" longos, {keeper['clearances_per_90']:.2f} bolas afastadas por 90 minutos)"
        )


def run(args):
    dataset = load_dataset(args.data, args.min_minutes)
    scorer = build_scorer(dataset, args.tau)
    check_team_size(args.team_size, len(dataset.players))

    if args.formation is None:
        quotas = ask_formation(dataset.positions, args.team_size)
    else:
        quotas = parse_formation(args.formation, dataset.positions, args.team_size)

    config = GAConfig(args.iterations, args.population, args.stagnation, args.mutations)
    seed = secrets.randbelow(2**32) if args.seed is None else args.seed
    print()
    result = run_ga(
        scorer, dataset.positions, quotas, args.team_size, config, seed, show_progress
    )
    print()

    print(f"\nNota do time: {result.score:.4f} (tau {args.tau}, semente {seed})")
    print("O time alcança o tau nessa fração dos pares de critérios.\n")
    print_team(dataset, result.team)

    finish_with_radar(
        args, lambda path, show: team_radar(dataset, scorer, list(result.team), quotas, path, show)
    )


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        run(args)
    except ValueError as error:
        raise SystemExit(f"Erro: {error}") from None
    except (EOFError, KeyboardInterrupt):
        raise SystemExit("\nNenhuma formação informada.") from None


if __name__ == "__main__":
    main()

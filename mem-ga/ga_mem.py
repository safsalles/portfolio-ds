"""GA-MEM: sugere as contratações que mais melhoram a complementação de um time.

Para rodar: python ga_mem.py

Usa a mesma nota e os mesmos dados do MEM-GA. Em vez de montar um time do zero, parte dos
10 jogadores de linha com mais minutos em um clube e procura quem deve entrar no lugar de
quem. Com uma contratação, testa todos os candidatos. Com duas ou mais, o algoritmo
genético busca a melhor combinação.
"""

import argparse
import csv
import secrets
import sys
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from mem_ga import (
    DEFAULT_DATA_DIR,
    DEFAULT_MIN_MINUTES,
    GAConfig,
    build_scorer,
    load_dataset,
    pitch_lines,
    rank_goalkeepers,
    run_ga,
    show_progress,
)

# Times reais ficam longe do melhor time possível, então o corte é menor que o do MEM-GA.
DEFAULT_TAU = 0.36
DEFAULT_ITERATIONS = 3000
STARTERS = 10
TOP_OPTIONS = 5
ANY_POSITION_WORDS = {"qualquer", "any"}


@dataclass(frozen=True)
class Signing:
    rating: tuple[float, float]
    swaps: tuple[tuple[int, int], ...]  # (quem sai, quem entra)
    team: tuple[int, ...]


# ======================================================================================
# CLUBES
# ======================================================================================

def _plain(text):
    """Tira acentos e maiúsculas, para aceitar `sao paulo` no lugar de `São Paulo`."""
    decomposed = unicodedata.normalize("NFKD", text.strip().casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def load_clubs(folder, dataset):
    """Devolve os clubes em ordem alfabética, como {sigla: nome}. O clubs.csv é opcional."""
    names = {}
    path = Path(folder) / "clubs.csv"
    if path.is_file():
        with path.open(encoding="utf-8-sig", newline="") as file:
            names = {row["code"].strip(): row["name"].strip() for row in csv.DictReader(file)}
    codes = {str(code): names.get(str(code), str(code)) for code in np.unique(dataset.clubs)}
    return dict(sorted(codes.items(), key=lambda item: _plain(item[1])))


def parse_club(text, clubs):
    """Aceita o número da lista, o nome ou a sigla do clube."""
    answer = _plain(text)
    if answer.isdigit() and 1 <= int(answer) <= len(clubs):
        return list(clubs)[int(answer) - 1]
    for code, name in clubs.items():
        if answer in (_plain(code), _plain(name)):
            return code
    raise ValueError(f"Não achei o clube {text.strip()!r}. Use o número, o nome ou a sigla.")


# ======================================================================================
# CONTRATAÇÕES
# ======================================================================================

def starters(dataset, club, size=STARTERS):
    """Os jogadores de linha com mais minutos no clube."""
    players = np.flatnonzero(dataset.clubs == club)
    ranking = players[np.argsort(-dataset.minutes[players], kind="stable")]
    return [int(player) for player in ranking[:size]]


def candidates_for(dataset, club, position=None):
    outside = dataset.clubs != club
    if position is not None:
        outside &= dataset.positions == position
    return [int(player) for player in np.flatnonzero(outside)]


class SigningSearch:
    """Avalia pacotes de contratações. O `run_ga` usa esta classe como nota do time."""

    def __init__(self, scorer, dataset, team):
        self.scorer = scorer
        self.payment = scorer.payment
        self.positions = dataset.positions
        self.team = tuple(team)
        self.results = {}

    def rate(self, incoming):
        return self.evaluate(incoming).rating

    def evaluate(self, incoming):
        key = tuple(sorted(incoming))
        if key not in self.results:
            self.results[key] = self._best_swaps(key)
        return self.results[key]

    def _best_swaps(self, incoming):
        """Coloca cada contratado no lugar do titular cuja saída mais melhora a nota."""
        team = list(self.team)
        available = list(self.team)
        swaps = []
        for player in incoming:
            same_position = [p for p in available if self.positions[p] == self.positions[player]]
            rating, leaving = max(
                (self.scorer.rate([player if p == out else p for p in team]), out)
                for out in same_position or available
            )
            team[team.index(leaving)] = player
            available.remove(leaving)
            swaps.append((leaving, player))
        return Signing(rating, tuple(swaps), tuple(team))


def suggest(scorer, dataset, team, candidates, signings=1, config=None, seed=None, on_progress=None):
    """Devolve os pacotes avaliados, do melhor para o pior."""
    search = SigningSearch(scorer, dataset, team)
    if signings == 1:
        for player in candidates:
            search.evaluate((player,))
    else:
        labels = np.full(len(dataset.players), "fora")
        labels[candidates] = "novo"
        config = config or GAConfig(iterations=DEFAULT_ITERATIONS)
        run_ga(search, labels, {"novo": signings}, signings, config, seed, on_progress)
    return sorted(search.results.values(), key=lambda signing: signing.rating, reverse=True)


# ======================================================================================
# LINHA DE COMANDO
# ======================================================================================

def build_parser():
    defaults = GAConfig(iterations=DEFAULT_ITERATIONS)
    parser = argparse.ArgumentParser(
        prog="python ga_mem.py",
        description="Sugere as contratações que mais melhoram a complementação de um time.",
    )
    parser.add_argument("--club", help="número, nome ou sigla; se ficar de fora, o programa pergunta")
    parser.add_argument("--position", help="posição a contratar, ou 'qualquer'")
    parser.add_argument("--signings", type=int, help="quantidade de contratações")
    parser.add_argument("--data", default=DEFAULT_DATA_DIR, help="pasta com os arquivos CSV")
    parser.add_argument("--min-minutes", type=int, default=DEFAULT_MIN_MINUTES)
    parser.add_argument("--tau", type=float, default=DEFAULT_TAU, help="tau de corte do grupo")
    parser.add_argument("--seed", type=int, help="semente, para repetir um resultado")
    parser.add_argument("--iterations", type=int, default=defaults.iterations)
    parser.add_argument("--population", type=int, default=defaults.population)
    return parser


def ask(question, parse):
    while True:
        try:
            return parse(input(question))
        except ValueError as error:
            print(error)


def ask_club(clubs):
    print("Clubes:")
    for number, (code, name) in enumerate(clubs.items(), start=1):
        print(f"  {number:>2}. {name} ({code})")
    return ask("Qual clube? ", lambda text: parse_club(text, clubs))


def parse_position(text, positions):
    answer = text.strip()
    if answer.casefold() in ANY_POSITION_WORDS:
        return None
    if answer.upper() in positions:
        return answer.upper()
    raise ValueError(f"Não achei a posição {answer!r}. Use {', '.join(positions)} ou 'qualquer'.")


def parse_mode(text):
    if text.strip() in ("1", "2"):
        return text.strip()
    raise ValueError("Responda 1 ou 2.")


def ask_position(positions):
    print("\n  1. Escolher a posição da contratação")
    print("  2. Deixar o método sugerir de qualquer posição")
    if ask("Qual opção? ", parse_mode) == "2":
        return None
    question = f"Qual posição ({', '.join(positions)})? "
    return ask(question, lambda text: parse_position(text, positions))


def parse_signings(text, limit):
    answer = text.strip() or "1"
    if answer.isdigit() and 1 <= int(answer) <= limit:
        return int(answer)
    raise ValueError(f"Escolha um número de 1 a {limit}.")


def print_lineup(dataset, keeper, team):
    club_view = replace(dataset, goalkeeper=keeper)
    for line in pitch_lines(club_view, dataset.payment.sum(axis=1), team):
        print(f"  {line}")


def describe(dataset, signing):
    return ", ".join(
        f"{dataset.players[arrival]} no lugar de {dataset.players[leaving]}"
        for leaving, arrival in signing.swaps
    )


def run(args):
    dataset = load_dataset(args.data, args.min_minutes)
    clubs = load_clubs(args.data, dataset)
    club = ask_club(clubs) if args.club is None else parse_club(args.club, clubs)

    positions = [str(position) for position in np.unique(dataset.positions)]
    if args.position is None:
        position = ask_position(positions)
    else:
        position = parse_position(args.position, positions)

    candidates = candidates_for(dataset, club, position)
    team = starters(dataset, club)
    limit = min(len(team), len(candidates))
    if args.signings is None:
        question = f"Quantas contratações (1 a {limit})? "
        signings = ask(question, lambda text: parse_signings(text, limit))
    else:
        signings = parse_signings(str(args.signings), limit)

    scorer = build_scorer(dataset, len(team), args.tau)
    config = GAConfig(iterations=args.iterations, population=args.population)
    seed = secrets.randbelow(2**32) if args.seed is None else args.seed
    print()
    options = suggest(
        scorer, dataset, team, candidates, signings, config, seed,
        show_progress if signings > 1 else None,
    )
    if signings > 1:
        print()

    current = scorer.rate(team)[0]
    best = options[0]
    print(f"\n{clubs[club]}: nota atual {current:.4f} (tau {args.tau})")
    print(f"Com a melhor opção: nota {best.rating[0]:.4f} ({best.rating[0] - current:+.4f})\n")
    for leaving, arrival in best.swaps:
        print(f"  Sai {dataset.players[leaving]}, entra {dataset.players[arrival]}")
    print()

    keepers = [k for k in rank_goalkeepers(args.data, args.min_minutes) if k["team"] == club]
    keeper = max(keepers, key=lambda k: k["minutes"]) if keepers else None
    print_lineup(dataset, keeper, best.team)

    print("\nMelhores opções:")
    for number, option in enumerate(options[:TOP_OPTIONS], start=1):
        print(f"  {number}. {describe(dataset, option)}: nota {option.rating[0]:.4f}")


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        run(args)
    except ValueError as error:
        raise SystemExit(f"Erro: {error}") from None
    except (EOFError, KeyboardInterrupt):
        raise SystemExit("\nNenhuma resposta informada.") from None


if __name__ == "__main__":
    main()

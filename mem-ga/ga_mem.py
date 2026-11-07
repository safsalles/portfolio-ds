"""GA-MEM: lista as contratações que mais melhoram a complementação de um time.

Para rodar: python ga_mem.py

Usa a mesma nota e os mesmos dados do MEM-GA. Em vez de montar um time do zero, parte dos
10 jogadores de linha com mais minutos em um clube, testa cada candidato no lugar de cada
titular da posição dele e mostra as melhores opções. Cada opção é uma contratação só.
"""

import argparse
import csv
import sys
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from mem_ga import (
    DEFAULT_DATA_DIR,
    DEFAULT_MIN_MINUTES,
    DEFAULT_TAU,
    RADAR_COLORS,
    RADAR_MUTED,
    build_scorer,
    finish_with_radar,
    plot_radar,
    tau_argument,
    load_dataset,
    pitch_lines,
    rank_goalkeepers,
)

STARTERS = 10
DEFAULT_OPTIONS = 5
ANY_POSITION_WORDS = {"qualquer", "any"}


@dataclass(frozen=True)
class Signing:
    rating: tuple[float, float]
    leaving: int
    arrival: int
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
    """Os jogadores com mais minutos no clube, com pelo menos um em cada posição.

    Só por minutos, o Vasco ficaria sem nenhum atacante, e não haveria quem substituir.
    """
    players = np.flatnonzero(dataset.clubs == club)
    ranking = [int(p) for p in players[np.argsort(-dataset.minutes[players], kind="stable")]]
    first_by_position = {}
    for player in ranking:
        first_by_position.setdefault(str(dataset.positions[player]), player)

    team = list(first_by_position.values())[:size]
    team += [player for player in ranking if player not in team][: size - len(team)]
    return sorted(team, key=ranking.index)


def candidates_for(dataset, club, position=None):
    """Jogadores de outros clubes, nas posições que têm titular para ser substituído."""
    outside = (dataset.clubs != club) & np.isin(
        dataset.positions, dataset.positions[starters(dataset, club)]
    )
    if position is not None:
        outside &= dataset.positions == position
    return [int(player) for player in np.flatnonzero(outside)]


def best_swap(scorer, dataset, team, arrival):
    """Coloca o contratado no lugar do titular da posição dele que mais melhora a nota."""
    options = []
    for leaving in team:
        if dataset.positions[leaving] == dataset.positions[arrival]:
            new_team = tuple(arrival if player == leaving else player for player in team)
            options.append(Signing(scorer.rate(new_team), leaving, arrival, new_team))
    return max(options, key=lambda signing: signing.rating)


def suggest(scorer, dataset, team, candidates):
    """Devolve a melhor troca de cada candidato, da melhor para a pior."""
    options = [best_swap(scorer, dataset, team, player) for player in candidates]
    return sorted(options, key=lambda signing: signing.rating, reverse=True)


# ======================================================================================
# LINHA DE COMANDO
# ======================================================================================

def build_parser():
    parser = argparse.ArgumentParser(
        prog="python ga_mem.py",
        description="Lista as contratações que mais melhoram a complementação de um time.",
    )
    parser.add_argument("--club", help="número, nome ou sigla; se ficar de fora, o programa pergunta")
    parser.add_argument("--position", help="posição a contratar, ou 'qualquer'")
    parser.add_argument("--options", type=int, help="quantas opções mostrar")
    parser.add_argument("--data", default=DEFAULT_DATA_DIR, help="pasta com os arquivos CSV")
    parser.add_argument("--min-minutes", type=int, default=DEFAULT_MIN_MINUTES)
    parser.add_argument("--tau", type=tau_argument, default=DEFAULT_TAU, help="tau de corte do grupo")
    parser.add_argument("--radar", type=Path, help="salva o gráfico de radar neste arquivo (.png)")
    parser.add_argument("--no-plot", action="store_true", help="não abre a janela do gráfico no final")
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


def parse_options(text, limit):
    answer = text.strip() or str(min(DEFAULT_OPTIONS, limit))
    if answer.isdigit() and 1 <= int(answer) <= limit:
        return int(answer)
    raise ValueError(f"Escolha um número de 1 a {limit}.")


def print_lineup(dataset, keeper, team):
    club_view = replace(dataset, goalkeeper=keeper)
    for line in pitch_lines(club_view, dataset.payment.sum(axis=1), team):
        print(f"  {line}")


def describe(dataset, signing):
    return f"{dataset.players[signing.arrival]} no lugar de {dataset.players[signing.leaving]}"


def signing_radar(dataset, scorer, team, signing, path=None, show=False):
    """Mostra o time antes e depois da opção, e quem sai contra quem entra."""
    payment = scorer.payment
    before, after = (f"{scorer.rate(t)[0]:.4f}".replace(".", ",") for t in (team, signing.team))
    leaving, arrival = dataset.players[signing.leaving], dataset.players[signing.arrival]
    plot_radar(dataset.criteria, [
        (f"Time: nota {before} antes, {after} depois", [
            ("Antes", payment[list(team)].mean(axis=0), RADAR_MUTED, "dash"),
            ("Depois", payment[list(signing.team)].mean(axis=0), RADAR_COLORS[0], "fill"),
        ]),
        (f"Sai {leaving}, entra {arrival}", [
            (f"Sai {leaving}", payment[signing.leaving], RADAR_COLORS[1], "line"),
            (f"Entra {arrival}", payment[signing.arrival], RADAR_COLORS[2], "fill"),
        ]),
    ], path, show)


def run(args):
    dataset = load_dataset(args.data, args.min_minutes)
    clubs = load_clubs(args.data, dataset)
    club = ask_club(clubs) if args.club is None else parse_club(args.club, clubs)

    team = starters(dataset, club)
    positions = sorted({str(dataset.positions[player]) for player in team})
    if args.position is None:
        position = ask_position(positions)
    else:
        position = parse_position(args.position, positions)

    candidates = candidates_for(dataset, club, position)
    if not candidates:
        where = "" if position is None else f" na posição {position}"
        raise ValueError(
            f"Não há candidatos para {clubs[club]}{where}: nenhum jogador de outro clube "
            f"com {args.min_minutes} minutos ou mais."
        )
    if args.options is None:
        limit = len(candidates)
        question = f"Quantas opções mostrar (1 a {limit}, Enter para {min(DEFAULT_OPTIONS, limit)})? "
        amount = ask(question, lambda text: parse_options(text, limit))
    else:
        amount = parse_options(str(args.options), len(candidates))

    scorer = build_scorer(dataset, args.tau)
    options = suggest(scorer, dataset, team, candidates)

    rating = scorer.rate(team)
    current = rating[0]
    best = options[0]
    improves = best.rating > rating
    if len(team) < STARTERS:
        print(
            f"\nAviso: {clubs[club]} tem só {len(team)} jogadores de linha com "
            f"{args.min_minutes} minutos ou mais. A nota foi calculada com {len(team)} "
            f"jogadores, e não é comparável com a de times de {STARTERS}."
        )
    print(f"\n{clubs[club]}: nota atual {current:.4f} (tau {args.tau})")
    if improves:
        print(f"Com a melhor opção: nota {best.rating[0]:.4f} ({best.rating[0] - current:+.4f})\n")
        print(f"  Sai {dataset.players[best.leaving]}, entra {dataset.players[best.arrival]}\n")
    else:
        print("Nenhuma opção melhora o time, então ele fica como está.\n")

    keepers = [k for k in rank_goalkeepers(args.data, args.min_minutes) if k["team"] == club]
    keeper = max(keepers, key=lambda k: k["minutes"]) if keepers else None
    print_lineup(dataset, keeper, best.team if improves else team)

    print("\nMelhores opções:" if improves else "\nOpções que menos pioram:")
    for number, option in enumerate(options[:amount], start=1):
        gain = option.rating[0] - current
        print(f"  {number}. {describe(dataset, option)}: nota {option.rating[0]:.4f} ({gain:+.4f})")

    finish_with_radar(args, lambda path, show: signing_radar(dataset, scorer, team, best, path, show))


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

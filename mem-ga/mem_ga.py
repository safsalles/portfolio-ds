"""MEM-GA: monta um time de futebol com o Método de Escolha Múltipla e algoritmo genético.

Para rodar: python mem_ga.py

O arquivo segue a ordem do processo: dados, nota, formação, algoritmo genético e
linha de comando.
"""

import argparse
import csv
import secrets
import sys
from dataclasses import dataclass
from itertools import combinations
from math import comb, prod
from pathlib import Path

import numpy as np


# ======================================================================================
# DADOS (equivalente ao `impmem.m`)
# ======================================================================================

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_MIN_MINUTES = 850


class DataError(ValueError):
    """Os arquivos de dados não seguem o formato esperado."""


@dataclass(frozen=True)
class Dataset:
    players: list[str]  # nome com a sigla do clube, como "Hernanes (SAO)"
    positions: np.ndarray
    criteria: list[str]
    payment: np.ndarray  # jogadores x critérios, normalizado entre 0 e 1
    weights: np.ndarray
    complementarity: np.ndarray  # critérios x critérios
    goalkeeper: str | None = None
    goalkeeper_save_rate: float | None = None


def normalize(values, direction, cuts):
    """Aplica os cortes e leva cada critério para a escala de 0 a 1.

    Com corte, o valor vira 1 quando é maior ou igual ao corte e 0 caso contrário.
    Sem corte (NaN), o critério segue contínuo. Depois, 1 sempre é o melhor
    desempenho: em critérios de custo (direction 0), a escala é invertida.
    """
    values = np.asarray(values, float)
    cuts = np.asarray(cuts, float)
    prepared = np.where(np.isnan(cuts), values, (values >= cuts).astype(float))

    high, low = prepared.max(axis=0), prepared.min(axis=0)
    is_benefit = np.asarray(direction) >= 1
    best = np.where(is_benefit, high, low)
    worst = np.where(is_benefit, low, high)

    # Um critério constante não diferencia ninguém. No MATLAB, ele dividia por zero.
    spread = np.where(best == worst, 1.0, best - worst)
    return (prepared - worst) / spread


def _read_csv(path):
    if not path.is_file():
        raise DataError(f"Arquivo não encontrado: {path}")
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def _number(text, where):
    try:
        return float(text)
    except (TypeError, ValueError):
        raise DataError(f"Valor inválido em {where}: {text!r}") from None


def _require_columns(found, required, filename):
    missing = [column for column in required if column not in found]
    if missing:
        raise DataError(f"Faltam colunas em {filename}: {', '.join(missing)}")


def _read_criteria(folder):
    columns, rows = _read_csv(folder / "criteria.csv")
    _require_columns(columns, ["criterion", "direction", "weight", "cut"], "criteria.csv")
    if not rows:
        raise DataError("criteria.csv não tem nenhum critério")

    names = [row["criterion"].strip() for row in rows]
    if len(set(names)) != len(names):
        raise DataError("criteria.csv tem critérios repetidos")

    direction = np.array([_number(r["direction"], f"direction de {r['criterion']}") for r in rows])
    if not np.isin(direction, (0, 1)).all():
        raise DataError("Em criteria.csv, direction deve ser 1 (benefício) ou 0 (custo)")

    weights = np.array([_number(r["weight"], f"weight de {r['criterion']}") for r in rows])
    cuts = np.array(
        [
            np.nan if not (r["cut"] or "").strip() else _number(r["cut"], f"cut de {r['criterion']}")
            for r in rows
        ]
    )
    return names, direction, weights, cuts


def _read_players(folder, criteria, min_minutes):
    columns, rows = _read_csv(folder / "players.csv")
    _require_columns(columns, ["player", "team", "position", "minutes", *criteria], "players.csv")
    rows = [row for row in rows if _number(row["minutes"], row["player"]) >= min_minutes]
    if not rows:
        raise DataError(f"players.csv não tem jogadores com {min_minutes} minutos ou mais")

    totals = np.array(
        [[_number(row[name], f"{row['player']} / {name}") for name in criteria] for row in rows]
    )
    minutes = np.array([float(row["minutes"]) for row in rows])
    values = totals / minutes[:, None] * 90
    return (
        [f"{row['player'].strip()} ({row['team'].strip()})" for row in rows],
        np.array([row["position"].strip().upper() for row in rows]),
        values,
    )


def _read_complementarity(folder, criteria):
    columns, rows = _read_csv(folder / "matrix_c.csv")
    _require_columns(columns, ["criterion", *criteria], "matrix_c.csv")
    by_name = {row["criterion"].strip(): row for row in rows}
    _require_columns(by_name, criteria, "matrix_c.csv (linhas)")

    matrix = np.full((len(criteria), len(criteria)), np.nan)
    for i, row_name in enumerate(criteria):
        for j, column_name in enumerate(criteria):
            cell = (by_name[row_name][column_name] or "").strip()
            if cell:
                matrix[i, j] = _number(cell, f"matrix_c.csv ({row_name}, {column_name})")

    if np.isnan(matrix[np.triu_indices(len(criteria), k=1)]).any():
        raise DataError("matrix_c.csv precisa ter todos os valores acima da diagonal")
    return matrix


def _read_goalkeeper(folder, min_minutes):
    """Escolhe o goleiro com o maior aproveitamento de defesas. O arquivo é opcional."""
    if not (folder / "goalkeepers.csv").is_file():
        return None, None

    columns, rows = _read_csv(folder / "goalkeepers.csv")
    required = ["player", "team", "minutes", "saves", "goals_conceded"]
    _require_columns(columns, required, "goalkeepers.csv")
    candidates = []
    for row in rows:
        saves = _number(row["saves"], f"saves de {row['player']}")
        conceded = _number(row["goals_conceded"], f"goals_conceded de {row['player']}")
        if _number(row["minutes"], row["player"]) >= min_minutes and saves + conceded > 0:
            name = f"{row['player'].strip()} ({row['team'].strip()})"
            candidates.append((saves / (saves + conceded), name))
    if not candidates:
        return None, None
    save_rate, name = max(candidates)
    return name, save_rate


def load_dataset(folder=DEFAULT_DATA_DIR, min_minutes=DEFAULT_MIN_MINUTES):
    folder = Path(folder)
    criteria, direction, weights, cuts = _read_criteria(folder)
    players, positions, values = _read_players(folder, criteria, min_minutes)
    goalkeeper, save_rate = _read_goalkeeper(folder, min_minutes)
    return Dataset(
        players=players,
        positions=positions,
        criteria=criteria,
        payment=normalize(values, direction, cuts),
        weights=weights,
        complementarity=_read_complementarity(folder, criteria),
        goalkeeper=goalkeeper,
        goalkeeper_save_rate=save_rate,
    )


# ======================================================================================
# NOTA DO TIME (regra do tau por grupo, do `memc.m`)
#
# Para cada combinação de critérios, o time recebe um valor: o desempenho médio dos
# jogadores naqueles critérios, multiplicado pelo peso e pela complementaridade da
# combinação. A nota é a fração de combinações em que o valor alcança o tau. Um time com
# buracos falha em toda combinação que inclui o buraco, então um jogador vale mais ou
# menos conforme o que os outros já cobrem.
# ======================================================================================

DEFAULT_TAU = 0.36
MAX_COMBINATIONS = 500_000


@dataclass(frozen=True)
class TeamScorer:
    payment: np.ndarray
    combo_matrix: np.ndarray  # critérios x combinações
    tau: float

    def combo_values(self, team):
        """Valor do time em cada combinação de critérios (a linha de `MBline`)."""
        return self.payment[list(team)].mean(axis=0) @ self.combo_matrix

    def rate(self, team):
        """Devolve a nota e, para desempate, o valor médio do time.

        A maioria dos times sorteados fica com nota zero. O desempate dá ao algoritmo
        genético uma direção até ele chegar aos times que alcançam o tau.
        """
        values = self.combo_values(team)
        return float((values >= self.tau).mean()), float(values.mean())


def build_scorer(dataset, team_size, tau=DEFAULT_TAU):
    n_criteria = len(dataset.criteria)
    if not 2 <= team_size <= n_criteria:
        raise ValueError(
            f"O tamanho do time ({team_size}) precisa estar entre 2 e o número "
            f"de critérios ({n_criteria}), porque ele define as combinações de critérios."
        )
    if comb(n_criteria, team_size) > MAX_COMBINATIONS:
        raise ValueError(
            f"{comb(n_criteria, team_size)} combinações de critérios é mais do que o "
            f"limite de {MAX_COMBINATIONS}."
        )

    combos = np.array(list(combinations(range(n_criteria), team_size)))
    pairs = list(combinations(range(team_size), 2))
    complementarity = dataset.complementarity
    pair_mean = sum(complementarity[combos[:, a], combos[:, b]] for a, b in pairs) / len(pairs)
    combo_factor = dataset.weights[combos].mean(axis=1) * pair_mean

    combo_matrix = np.zeros((n_criteria, len(combos)))
    combo_matrix[combos.T, np.arange(len(combos))] = combo_factor / team_size
    return TeamScorer(dataset.payment, combo_matrix, tau)


# ======================================================================================
# FORMAÇÃO
# ======================================================================================

FREE_WORDS = {"", "livre", "free"}

# Para mudar um atalho ou criar outro, basta editar esta tabela.
PRESETS = {
    "4-4-2": {"ZAG": 2, "LE": 1, "LD": 1, "VOL": 2, "MEI": 2, "ATA": 2},
    "4-3-3": {"ZAG": 2, "LE": 1, "LD": 1, "VOL": 1, "MEI": 2, "ATA": 3},
    "4-2-3-1": {"ZAG": 2, "LE": 1, "LD": 1, "VOL": 2, "MEI": 3, "ATA": 1},
    "3-5-2": {"ZAG": 3, "LE": 1, "LD": 1, "VOL": 2, "MEI": 1, "ATA": 2},
}


class FormationError(ValueError):
    """A formação digitada não pode ser montada com estes dados."""


def _parse_custom(text):
    quotas = {}
    for part in text.split(","):
        position, separator, amount = part.partition("=")
        position = position.strip().upper()
        if not separator or not position or not amount.strip().isdigit():
            raise FormationError(
                f"Não entendi {text!r}. Use um atalho ({', '.join(PRESETS)}), "
                "'livre' ou o formato zag=2,le=1,ld=1,vol=2,mei=2,ata=2."
            )
        if position in quotas:
            raise FormationError(f"A posição {position} apareceu duas vezes.")
        quotas[position] = int(amount)
    return quotas


def parse_formation(text, positions, team_size=10):
    """Devolve as quotas por posição, ou None para o time livre."""
    text = text.strip()
    if text.lower() in FREE_WORDS:
        return None

    quotas = dict(PRESETS[text]) if text in PRESETS else _parse_custom(text)

    names, counts = np.unique(positions, return_counts=True)
    available = dict(zip(names.tolist(), counts.tolist()))
    for position, quota in quotas.items():
        if quota > available.get(position, 0):
            raise FormationError(
                f"A formação pede {quota} de {position}, mas os dados têm "
                f"{available.get(position, 0)}."
            )

    total = sum(quotas.values())
    if total != team_size:
        raise FormationError(f"A formação soma {total} jogadores, e o time precisa de {team_size}.")
    return quotas


# ======================================================================================
# ALGORITMO GENÉTICO (equivalente a `gene.m` e `generes.m`)
#
# O time livre e o time com formação usam o mesmo código. Sem formação, todos os
# jogadores ficam em uma única posição, com quota igual ao tamanho do time.
# `gcrom.m`/`testecrom.m` sorteiam os times iniciais, `recalCrom.m`/`respar.m` fazem o
# cruzamento e `gene.m`/`bla.m` fazem a mutação.
# ======================================================================================

MAX_REDRAWS = 1000
PROGRESS_STEP = 100


@dataclass(frozen=True)
class GAConfig:
    iterations: int = 10000
    population: int = 60
    stagnation: int = 14  # iterações sem melhora até a mutação (`mut` no MATLAB)
    mutation_attempts: int = 7  # tentativas em cada mutação (`tmut` no MATLAB)

    def __post_init__(self):
        if self.population < 2:
            raise ValueError("A população precisa ter pelo menos 2 times.")
        if min(self.iterations, self.stagnation, self.mutation_attempts) < 1:
            raise ValueError("Iterações, estagnação e mutações precisam ser pelo menos 1.")


@dataclass(frozen=True)
class GAResult:
    team: tuple[int, ...]
    score: float
    history: list[float]


class _Search:
    def __init__(self, scorer, positions, quotas, team_size, config, rng, on_progress):
        self.scorer = scorer
        self.on_progress = on_progress
        self.n_players = len(scorer.payment)
        self.config = config
        self.rng = rng
        if quotas is None:
            self.labels = np.full(self.n_players, "*")
            self.quotas = {"*": team_size}
        else:
            self.labels = np.asarray(positions)
            self.quotas = {position: quota for position, quota in quotas.items() if quota > 0}

    def _pick(self, candidates):
        """Sorteia, entre os candidatos, os jogadores de cada posição."""
        team = []
        for position, quota in self.quotas.items():
            pool = candidates[self.labels[candidates] == position]
            team.extend(self.rng.choice(pool, size=quota, replace=False).tolist())
        return tuple(sorted(team))

    def _rated(self, team):
        return self.scorer.rate(team), team

    def _possible_teams(self):
        return prod(comb(int((self.labels == p).sum()), q) for p, q in self.quotas.items())

    def _first_population(self):
        everyone = np.arange(self.n_players)
        target = min(self.config.population, self._possible_teams())
        teams = set()
        while len(teams) < target:
            teams.add(self._pick(everyone))
        return sorted((self._rated(team) for team in teams), key=lambda item: item[0])

    def _crossover(self, population):
        first, second = self.rng.integers(len(population), size=2)
        parents = np.union1d(population[first][1], population[second][1])
        return self._pick(parents)

    def _new_child(self, population, seen):
        child = self._crossover(population)
        if child in seen:
            current = {team for _, team in population}
            # O limite evita laço infinito quando a população já convergiu.
            for _ in range(MAX_REDRAWS):
                child = self._crossover(population)
                if child not in current:
                    break
        return child

    @staticmethod
    def _replace_worst(population, seen, rated_team):
        population.append(rated_team)
        population.sort(key=lambda item: item[0])
        del population[0]
        seen.update(team for _, team in population)

    def _mutate(self, best, population, seen):
        eligible = np.flatnonzero(np.isin(self.labels, list(self.quotas)))
        untested = set(eligible.tolist()) - set(best[1])

        for _ in range(self.config.mutation_attempts):
            # No MATLAB, a lista vazia gerava erro.
            if not untested:
                break
            newcomer = int(self.rng.choice(sorted(untested)))
            untested.discard(newcomer)

            slots = [
                slot
                for slot, player in enumerate(best[1])
                if self.labels[player] == self.labels[newcomer]
            ]
            mutant = list(best[1])
            mutant[int(self.rng.choice(slots))] = newcomer

            rated = self._rated(tuple(mutant))
            if rated[0] > best[0]:
                # Como no original, o time melhor vira o campeão, mas não entra na população.
                return rated
            self._replace_worst(population, seen, rated)
        return best

    def run(self):
        population = self._first_population()
        seen = {team for _, team in population}
        best = population[-1]
        stagnant = 0
        history = []

        total = self.config.iterations
        for iteration in range(1, total + 1):
            child = self._new_child(population, seen)
            self._replace_worst(population, seen, self._rated(child))

            if population[-1][0] > best[0]:
                best = population[-1]
                stagnant = 0
            else:
                stagnant += 1
                if stagnant == self.config.stagnation:
                    best = self._mutate(best, population, seen)
                    stagnant = 0
            history.append(best[0][0])
            if self.on_progress and (iteration % PROGRESS_STEP == 0 or iteration == total):
                self.on_progress(iteration, total, best[0][0])

        return GAResult(team=best[1], score=best[0][0], history=history)


def run_ga(scorer, positions, quotas, team_size, config=None, seed=None, on_progress=None):
    """Roda a busca. `on_progress(iteração, total, melhor nota)` acompanha a evolução."""
    rng = np.random.default_rng(seed)
    search = _Search(
        scorer, positions, quotas, team_size, config or GAConfig(), rng, on_progress
    )
    return search.run()


# ======================================================================================
# LINHA DE COMANDO
# ======================================================================================

# Linhas do campo, do ataque para a defesa e da esquerda para a direita.
PITCH_ROWS = (("ATA",), ("MEI",), ("VOL",), ("LE", "ZAG", "LD"))
MAX_PER_PITCH_ROW = 4
PROGRESS_BAR_WIDTH = 30


def build_parser():
    defaults = GAConfig()
    parser = argparse.ArgumentParser(
        prog="python mem_ga.py",
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
    parser.add_argument("--tau", type=float, default=DEFAULT_TAU, help="tau de corte do grupo")
    parser.add_argument("--seed", type=int, help="semente, para repetir um resultado")
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


def spread(names, width):
    """Distribui os nomes de uma linha do campo, com a mesma folga entre eles."""
    gap, extra = divmod(width - sum(len(name) for name in names), len(names) + 1)
    line = "".join(" " * (gap + (i < extra)) + name for i, name in enumerate(names))
    return line.ljust(width)


def pitch_lines(dataset, strengths, team):
    """Desenha o time em campo. Com outras posições nos dados, não há o que desenhar."""
    known = {position for row in PITCH_ROWS for position in row}
    if any(dataset.positions[player] not in known for player in team):
        return []

    rows = []
    for row in PITCH_ROWS:
        players = sorted(
            (player for player in team if dataset.positions[player] in row),
            key=lambda player: (row.index(dataset.positions[player]), -strengths[player]),
        )
        for start in range(0, len(players), MAX_PER_PITCH_ROW):
            rows.append([dataset.players[p] for p in players[start:start + MAX_PER_PITCH_ROW]])
    if dataset.goalkeeper:
        rows.append([dataset.goalkeeper])

    width = max(sum(len(name) + 2 for name in row) + 2 for row in rows)
    goal_line = "+" + "[     ]".center(width, "-") + "+"
    blank = "|" + " " * width + "|"

    lines = [goal_line, blank]
    for index, row in enumerate(rows):
        if index == len(rows) // 2:
            lines += ["|" + "o".center(width, "-") + "|", blank]
        lines += ["|" + spread(row, width) + "|", blank]
    return [*lines, goal_line]


def print_team(dataset, team):
    strengths = dataset.payment.sum(axis=1)
    for line in pitch_lines(dataset, strengths, team):
        print(f"  {line}")
    print()

    order = sorted(team, key=lambda player: -strengths[player])
    width = max(len(dataset.players[player]) for player in order)
    print(f"  {'Jogador':<{width}}  {'Pos':<4}  Critérios atingidos")
    for player in order:
        print(
            f"  {dataset.players[player]:<{width}}  {dataset.positions[player]:<4}"
            f"  {strengths[player]:.4g} de {len(dataset.criteria)}"
        )
    if dataset.goalkeeper:
        print(f"\n  Goleiro: {dataset.goalkeeper}, {dataset.goalkeeper_save_rate:.1%} de defesas")


def run(args):
    dataset = load_dataset(args.data, args.min_minutes)
    scorer = build_scorer(dataset, args.team_size, args.tau)

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
    print("O time alcança o tau nessa fração das combinações de critérios.\n")
    print_team(dataset, result.team)


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

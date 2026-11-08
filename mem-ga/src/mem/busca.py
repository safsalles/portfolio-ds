"""As buscas do MEM: exaustiva, para problemas pequenos, e por algoritmo genético.

As duas funcionam com qualquer regra de `mem.regras`, porque só usam `rate(conjunto)`.
"""

from dataclasses import dataclass
from itertools import combinations
from math import comb, prod

import numpy as np

# ======================================================================================
# BUSCA EXAUSTIVA (como a tese: testa todas as combinações e mostra a ordem completa)
# ======================================================================================

MAX_EVALUATIONS = 20_000_000  # acima disso, testar tudo já não é prático


@dataclass(frozen=True)
class Choice:
    position: int
    alternatives: tuple[int, ...]
    score: float  # fração dos grupos de critérios que alcançam o tau


def exhaustive(rule, n_alternatives, size):
    """Equação 3.9: ordena todos os conjuntos pela nota. Empates ficam na mesma posição."""
    total = comb(n_alternatives, size) * rule.n_combos
    if total > MAX_EVALUATIONS:
        raise ValueError(f"Seriam {total} avaliações, demais para testar uma a uma.")
    sets = list(combinations(range(n_alternatives), size))
    scores = [rule.rate(chosen)[0] for chosen in sets]
    order = sorted(range(len(sets)), key=lambda row: (-scores[row], sets[row]))

    ranking = []
    for place, row in enumerate(order, start=1):
        tied = ranking and scores[row] == ranking[-1].score
        position = ranking[-1].position if tied else place
        ranking.append(Choice(position, sets[row], scores[row]))
    return ranking


def traditional_choice(payment, size, groups=None, quotas=None):
    """A escolha comum, sem o MEM: os de maior desempenho somado, respeitando as vagas."""
    strengths = np.asarray(payment).sum(axis=1)
    order = [int(i) for i in np.argsort(-strengths, kind="stable")]
    if quotas is None:
        return order[:size]
    chosen = []
    for group, quota in quotas.items():
        chosen += [i for i in order if groups[i] == group][:quota]
    return chosen


# ======================================================================================
# ALGORITMO GENÉTICO (equivalente a `gene.m` e `generes.m` da dissertação)
#
# Sem vagas, todas as alternativas ficam num grupo só, com vagas iguais ao tamanho do
# conjunto. `gcrom.m`/`testecrom.m` sorteiam os conjuntos iniciais, `recalCrom.m`/
# `respar.m` fazem o cruzamento e `gene.m`/`bla.m` fazem a mutação.
# ======================================================================================

MAX_REDRAWS = 1000
PROGRESS_STEP = 100


@dataclass(frozen=True)
class GAConfig:
    iterations: int = 15000
    population: int = 60
    stagnation: int = 14  # iterações sem melhora até a mutação (`mut` no MATLAB)
    mutation_attempts: int = 7  # tentativas em cada mutação (`tmut` no MATLAB)
    kick_size: int = 3  # alternativas trocadas de uma vez na mutação forte
    climb_every: int = 5  # mutações entre uma mutação forte e a seguinte

    def __post_init__(self):
        if self.population < 2:
            raise ValueError("A população precisa ter pelo menos 2 conjuntos.")
        if min(self.iterations, self.stagnation, self.mutation_attempts) < 1:
            raise ValueError("Iterações, estagnação e mutações precisam ser pelo menos 1.")
        if min(self.kick_size, self.climb_every) < 1:
            raise ValueError("A mutação forte precisa de valores de pelo menos 1.")


@dataclass(frozen=True)
class GAResult:
    team: tuple[int, ...]
    score: float
    history: list[float]


def check_size(size, n_alternatives):
    if size < 1:
        raise ValueError(f"O conjunto precisa ter pelo menos 1 alternativa, e veio {size}.")
    if size > n_alternatives:
        raise ValueError(f"O conjunto pede {size} alternativas, mas os dados têm só {n_alternatives}.")


class _Search:
    def __init__(self, rule, groups, quotas, size, config, rng, on_progress):
        self.rule = rule
        self.on_progress = on_progress
        self.n_alternatives = len(rule.payment)
        self.config = config
        self.rng = rng
        if quotas is None:
            check_size(size, self.n_alternatives)
            self.labels = np.full(self.n_alternatives, "*")
            self.quotas = {"*": size}
        else:
            self.labels = np.asarray(groups)
            self.quotas = {group: quota for group, quota in quotas.items() if quota > 0}
        self.pools = {g: np.flatnonzero(self.labels == g).tolist() for g in self.quotas}
        for group, quota in self.quotas.items():
            if quota > len(self.pools[group]):
                raise ValueError(
                    f"O grupo {group} tem {len(self.pools[group])} alternativas, e foram pedidas {quota}."
                )

    def _pick(self, candidates):
        """Sorteia, entre os candidatos, as alternativas de cada grupo."""
        team = []
        for group, quota in self.quotas.items():
            pool = candidates[self.labels[candidates] == group]
            team.extend(self.rng.choice(pool, size=quota, replace=False).tolist())
        return tuple(sorted(team))

    def _rated(self, team):
        return self.rule.rate(team), team

    def _possible_teams(self):
        return prod(comb(int((self.labels == g).sum()), q) for g, q in self.quotas.items())

    def _first_population(self):
        everyone = np.arange(self.n_alternatives)
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
                for slot, member in enumerate(best[1])
                if self.labels[member] == self.labels[newcomer]
            ]
            mutant = list(best[1])
            mutant[int(self.rng.choice(slots))] = newcomer

            rated = self._rated(tuple(mutant))
            if rated[0] > best[0]:
                # Como no original, o conjunto melhor vira o campeão, mas não entra na população.
                return rated
            self._replace_worst(population, seen, rated)
        return best

    def _kick(self, team):
        """Troca `kick_size` alternativas de uma vez, cada uma por outra do mesmo grupo."""
        team = list(team)
        spare = {g: sorted(set(pool) - set(team)) for g, pool in self.pools.items()}
        slots = [slot for slot, member in enumerate(team) if spare[self.labels[member]]]
        size = min(self.config.kick_size, len(slots))
        for slot in self.rng.choice(slots, size=size, replace=False).tolist():
            pool = spare[self.labels[team[slot]]]
            # Um grupo com poucas sobrando pode esgotar antes de `kick_size` trocas.
            if pool:
                team[slot] = pool.pop(int(self.rng.integers(len(pool))))
        return tuple(sorted(team))

    def _climb(self, team):
        """Troca uma alternativa por vez, dentro do mesmo grupo, enquanto a nota subir."""
        best = self._rated(team)
        team = list(team)
        improved = True
        while improved:
            improved = False
            for slot, member in enumerate(team):
                others = team[:slot] + team[slot + 1:]
                for newcomer in self.pools[self.labels[member]]:
                    if newcomer in team:
                        continue
                    rated = self._rated(tuple(sorted(others + [newcomer])))
                    if rated[0] > best[0]:
                        best, team[slot], improved = rated, newcomer, True
        return best

    def _strong_mutation(self, best, population, seen):
        rated = self._climb(self._kick(best[1]))
        if rated[0] < best[0]:
            return best
        # Cópias do mesmo conjunto na população travam o cruzamento em `_new_child`.
        if rated not in population:
            self._replace_worst(population, seen, rated)
        return rated

    def run(self):
        population = self._first_population()
        seen = {team for _, team in population}
        best = population[-1]
        stagnant = 0
        mutations = 0
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
                    mutations += 1
                    if mutations % self.config.climb_every == 0:
                        best = self._strong_mutation(best, population, seen)
            history.append(best[0][0])
            if self.on_progress and (iteration % PROGRESS_STEP == 0 or iteration == total):
                self.on_progress(iteration, total, best[0][0])

        return GAResult(team=best[1], score=best[0][0], history=history)


def run_ga(rule, groups, quotas, size, config=None, seed=None, on_progress=None):
    """Roda a busca. `on_progress(iteração, total, melhor nota)` acompanha a evolução.

    `groups` é o grupo de cada alternativa e `quotas` as vagas por grupo. Com `quotas`
    None, todas as alternativas disputam as `size` vagas.
    """
    rng = np.random.default_rng(seed)
    search = _Search(rule, groups, quotas, size, config or GAConfig(), rng, on_progress)
    return search.run()

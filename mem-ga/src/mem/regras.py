"""As duas regras de nota do MEM: a da tese (média) e a adaptação (mínimo no par).

As duas recebem um conjunto de alternativas e devolvem (nota, desempate). A nota é a
fração dos grupos de critérios em que o conjunto alcança o tau (Equações 3.8 e 3.9). O
desempate é a média de mínimo(valor, tau): mostra o quanto falta nos grupos que ainda
não passam, e dá ao algoritmo genético uma direção entre conjuntos com a mesma nota.
"""

from dataclasses import dataclass
from itertools import combinations
from math import comb, isfinite

import numpy as np

from mem.pesos import complementarity_from_data, group_weights
from mem.problema import normalize

MAX_MEAN_GROUPS = 10_000  # acima disso, a regra da média fica lenta demais para a busca


def _check(tau, n_criteria):
    if not (isfinite(tau) and tau > 0):
        raise ValueError(f"O tau precisa ser um número finito maior que 0, e veio {tau}.")
    if n_criteria < 2:
        raise ValueError("A nota precisa de pelo menos 2 critérios.")


@dataclass(frozen=True)
class MinimumRule:
    """Critérios 2 a 2, com o menor dos dois: um critério forte não cobre um fraco."""

    payment: np.ndarray  # alternativas x critérios, normalizado e ajustado pelo grupo
    first: np.ndarray  # primeiro critério de cada par
    second: np.ndarray  # segundo critério de cada par
    factor: np.ndarray  # peso médio x complementaridade de cada par
    tau: float

    @property
    def n_combos(self):
        return len(self.first)

    def combo_values(self, team):
        """Valor do conjunto em cada par de critérios."""
        means = self.payment[list(team)].mean(axis=0)
        return np.minimum(means[self.first], means[self.second]) * self.factor

    def rate(self, team):
        values = self.combo_values(team)
        return float((values >= self.tau).mean()), float(np.minimum(values, self.tau).mean())


@dataclass(frozen=True)
class MeanRule:
    """Critérios n a n, com n = tamanho do conjunto, e a média dentro do grupo (tese)."""

    payment: np.ndarray
    groups: np.ndarray  # índices dos critérios, um grupo por linha
    factor: np.ndarray  # média dos pesos x média de c nos pares do grupo (Equação 3.5)
    tau: float
    size: int

    @property
    def n_combos(self):
        return len(self.groups)

    def combo_values(self, team):
        """Equação 3.4: valor do conjunto em cada grupo de critérios."""
        means = self.payment[list(team)].mean(axis=0)
        return means[self.groups].mean(axis=1) * self.factor

    def rate(self, team):
        values = self.combo_values(team)
        # O arredondamento evita que um valor igual ao tau caia abaixo dele por erro de ponto flutuante.
        passed = values.round(12) >= self.tau
        return float(passed.mean()), float(np.minimum(values, self.tau).mean())


def minimum_rule(payment, weights, complementarity, tau):
    _check(tau, payment.shape[1])
    pairs = np.array(list(combinations(range(payment.shape[1]), 2)))
    first, second = pairs[:, 0], pairs[:, 1]
    factor = (weights[first] + weights[second]) / 2 * complementarity[first, second]
    return MinimumRule(payment, first, second, factor, tau)


def mean_rule(payment, weights, complementarity, tau, size):
    n_criteria = payment.shape[1]
    _check(tau, n_criteria)
    if not 2 <= size <= n_criteria:
        raise ValueError(f"O conjunto precisa ter de 2 a {n_criteria} alternativas, e veio {size}.")
    total = comb(n_criteria, size)
    if total > MAX_MEAN_GROUPS:
        raise ValueError(
            f"A regra da média teria {total} grupos de critérios por avaliação, acima do "
            f"teto de {MAX_MEAN_GROUPS}. Use menos critérios, um conjunto menor ou a regra do mínimo."
        )
    groups = list(combinations(range(n_criteria), size))
    factor = []
    for group in groups:
        c_mean = np.mean([complementarity[j, k] for j, k in combinations(group, 2)])
        factor.append(weights[list(group)].mean() * c_mean)
    return MeanRule(payment, np.array(groups), np.array(factor), tau, size)


def build_rule(problem, rule, tau, size=None):
    """Monta a regra `"media"` ou `"minimo"` a partir de um Problem.

    Com grupos, o desempenho é ajustado pelo peso de cada grupo. Sem a matriz C nos
    dados, a complementação é calculada deles.
    """
    payment = normalize(problem.values, problem.direction)
    if problem.groups is not None:
        payment = payment * group_weights(problem.values, problem.groups, problem.direction)
    complementarity = problem.complementarity
    if complementarity is None:
        complementarity = complementarity_from_data(problem.values, problem.groups)

    if rule == "minimo":
        return minimum_rule(payment, problem.weights, complementarity, tau)
    if rule == "media":
        if size is None:
            raise ValueError("A regra da média precisa do tamanho do conjunto.")
        return mean_rule(payment, problem.weights, complementarity, tau, size)
    raise ValueError(f"Regra desconhecida: {rule!r}. Use 'media' ou 'minimo'.")

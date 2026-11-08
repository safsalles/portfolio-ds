"""A função de entrada do pacote: `memga()` escolhe um conjunto de alternativas.

Ela junta o que está nos outros módulos: monta a regra de nota, roda a busca exaustiva ou
o algoritmo genético e compara o resultado com a escolha tradicional.
"""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from memga.busca import GAConfig, exhaustive, run_ga, traditional_choice
from memga.problema import Problem, load_problem, normalize
from memga.regras import build_rule

DEFAULT_TAU = 0.24
METHODS = ("exhaustive", "ga")
RULES = ("mean", "minimum")
_RULE_NAMES = {"mean": "media", "minimum": "minimo"}
DATA_DIR = Path(__file__).resolve().parent / "data"
EXAMPLES = {"small": "recruiting-small", "large": "recruiting-large"}


@dataclass(frozen=True)
class Ranked:
    position: int
    alternatives: tuple[str, ...]
    score: float


@dataclass
class MemgaResult:
    """O resultado de `memga()`.

    `team` e `score` valem para os dois métodos: com a busca exaustiva, é o primeiro
    conjunto da ordem. `ranking` só existe na busca exaustiva e `history` só no algoritmo
    genético. `traditional` é a escolha tradicional e a nota dela na mesma regra.
    """

    team: tuple[str, ...]
    score: float
    method: str
    rule: str
    tau: float
    size: int
    problem: Problem
    traditional: tuple[tuple[str, ...], float]
    quotas: dict | None = None
    seed: int | None = None
    ranking: list[Ranked] = field(default_factory=list)
    history: list[float] = field(default_factory=list)
    payment: np.ndarray | None = None

    def __str__(self):
        search = "exhaustive search" if self.method == "exhaustive" else "genetic algorithm"
        lines = [
            f"Multiple Choice Method: {search}, {self.rule} rule, tau {self.tau:g}",
            f"{len(self.problem.alternatives)} alternatives, {len(self.problem.criteria)} criteria, "
            f"selecting {self.size}",
            "",
        ]
        if self.method == "exhaustive":
            lines.append(f"Best sets ({len(self.ranking)} tested):")
            for item in self.ranking[:10]:
                lines.append(f"  {item.position:>3}. {', '.join(item.alternatives):<24} {item.score:6.1%}")
            if len(self.ranking) > 10:
                lines.append(f"  ... {len(self.ranking) - 10} more")
        else:
            lines.append(f"Selected: {', '.join(self.team)} ({self.score:.1%})")
            if self.seed is not None:
                lines.append(f"Seed: {self.seed}")
        names, score = self.traditional
        lines += ["", f"Traditional choice (best one by one): {', '.join(names)} ({score:.1%})"]
        if self.ranking and len(names) == self.size:
            place = next((r.position for r in self.ranking if set(r.alternatives) == set(names)), None)
            if place:
                lines.append(f"It ranks {place} in the Multiple Choice Method.")
        return "\n".join(lines)


def load_example(name="small"):
    """Carrega um dos exemplos que vêm com o pacote: "small" (8 candidatos) ou "large" (300)."""
    if name not in EXAMPLES:
        raise ValueError(f"Exemplo desconhecido: {name!r}. Use 'small' ou 'large'.")
    return load_problem(DATA_DIR / EXAMPLES[name])


def _check_quotas(quotas, problem):
    if quotas is None:
        return None
    if problem.groups is None:
        raise ValueError("`quotas` precisa de `groups` no problema.")
    unknown = sorted(set(quotas) - set(problem.groups.tolist()))
    if unknown:
        raise ValueError(f"`quotas` cita grupos que não estão no problema: {', '.join(unknown)}.")
    if any(int(q) != q or q < 0 for q in quotas.values()):
        raise ValueError("`quotas` precisa ter números inteiros, de zero para cima.")
    quotas = {group: int(q) for group, q in quotas.items() if q > 0}
    if not quotas:
        raise ValueError("`quotas` precisa pedir pelo menos 1 alternativa.")
    return quotas


def memga(problem, size=None, method="exhaustive", rule=None, tau=DEFAULT_TAU, quotas=None,
          config=None, seed=None, on_progress=None):
    """Escolhe o conjunto de alternativas que mais se complementam.

    Parâmetros:
        problem: um `Problem`, de `load_problem` ou `load_example`.
        size: quantas alternativas escolher. Pode faltar quando há `quotas`.
        method: "exhaustive" (testa todas as combinações e devolve a ordem completa) ou
            "ga" (algoritmo genético, para problemas grandes demais para testar tudo).
        rule: "mean" (a regra da tese) ou "minimum" (critérios 2 a 2, com o menor dos dois).
            Por padrão, "mean" na busca exaustiva e "minimum" no algoritmo genético.
        tau: o corte; uma combinação de critérios conta quando o valor chega nele.
        quotas: vagas por grupo, como {"analyst": 2, "manager": 1}. Precisa de `groups`.
        config: um `GAConfig`, para ajustar o algoritmo genético.
        seed: semente, para repetir um resultado do algoritmo genético.
        on_progress: função (iteração, total, melhor nota) chamada durante o algoritmo genético.
    """
    if method not in METHODS:
        raise ValueError(f"Método desconhecido: {method!r}. Use 'exhaustive' ou 'ga'.")
    if rule is None:
        rule = "mean" if method == "exhaustive" else "minimum"
    if rule not in RULES:
        raise ValueError(f"Regra desconhecida: {rule!r}. Use 'mean' ou 'minimum'.")

    quotas = _check_quotas(quotas, problem)
    if size is None:
        if quotas is None:
            raise ValueError("Informe `size`, quantas alternativas escolher.")
        size = sum(quotas.values())
    elif int(size) != size or size < 1:
        raise ValueError(f"`size` precisa ser um número inteiro de pelo menos 1, e veio {size}.")
    elif quotas is not None and size != sum(quotas.values()):
        raise ValueError(f"`size` é {size}, mas `quotas` soma {sum(quotas.values())}.")
    size = int(size)
    if size > len(problem.alternatives):
        raise ValueError(
            f"O conjunto pede {size} alternativas, mas os dados têm só {len(problem.alternatives)}."
        )

    fitted = build_rule(problem, _RULE_NAMES[rule], tau, size=size)
    names = problem.alternatives
    normalized = normalize(problem.values, problem.direction)
    weights = problem.weights if problem.weights.sum() > 0 else np.ones_like(problem.weights)
    chosen = traditional_choice(normalized * weights, size, problem.groups, quotas)
    traditional = (tuple(names[i] for i in chosen), fitted.rate(tuple(sorted(chosen)))[0])

    result = dict(method=method, rule=rule, tau=tau, size=size, problem=problem,
                  traditional=traditional, quotas=quotas, seed=seed, payment=fitted.payment)
    if method == "exhaustive":
        ranking = [
            Ranked(c.position, tuple(names[i] for i in c.alternatives), c.score)
            for c in exhaustive(fitted, len(names), size, problem.groups, quotas)
        ]
        return MemgaResult(team=ranking[0].alternatives, score=ranking[0].score, ranking=ranking, **result)

    found = run_ga(fitted, problem.groups, quotas, size, config or GAConfig(), seed, on_progress)
    return MemgaResult(team=tuple(names[i] for i in found.team), score=found.score,
                       history=found.history, **result)

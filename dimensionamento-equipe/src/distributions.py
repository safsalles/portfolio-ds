"""Distribuições escolhíveis pelo usuário e seus amostradores.

Único lugar com a lista de distribuições (analisador, cenário e simulador usam isto).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

Sampler = Callable[[np.random.Generator, int], np.ndarray]

# nome -> parâmetros exigidos
DISTRIBUTIONS: dict[str, tuple[str, ...]] = {
    "expon": ("mean",),
    "lognormal": ("mean", "cv"),
    "gamma": ("mean", "cv"),
    "weibull": ("shape", "scale"),
    "erlang": ("k", "mean"),
    "normal": ("mean", "sd"),
    "triangular": ("low", "mode", "high"),
    "uniform": ("low", "high"),
    "beta": ("low", "high", "a", "b"),
}
MAX_TRUNCATION_ROUNDS = 100


@dataclass(frozen=True)
class DistSpec:
    dist: str
    params: dict = field(default_factory=dict)

    def __hash__(self):
        return hash((self.dist, tuple(sorted(self.params.items()))))


def _check(spec: DistSpec) -> dict:
    if spec.dist not in DISTRIBUTIONS:
        raise ValueError(f"distribuição desconhecida: {spec.dist!r} (use {sorted(DISTRIBUTIONS)})")
    need = set(DISTRIBUTIONS[spec.dist])
    got = set(spec.params)
    if got != need:
        raise ValueError(f"{spec.dist}: parâmetros esperados {sorted(need)}, recebidos {sorted(got)}")
    p = {k: float(v) for k, v in spec.params.items()}
    if not all(math.isfinite(v) for v in p.values()):
        raise ValueError(f"{spec.dist}: parâmetros devem ser finitos")
    return p


def build_sampler(spec: DistSpec) -> Sampler:
    p = _check(spec)
    d = spec.dist
    if d == "expon":
        if p["mean"] <= 0:
            raise ValueError("expon: mean deve ser > 0")
        return lambda rng, n: rng.exponential(p["mean"], n)
    if d == "lognormal":
        if p["mean"] <= 0 or p["cv"] <= 0:
            raise ValueError("lognormal: mean e cv devem ser > 0")
        s2 = math.log(1 + p["cv"] ** 2)
        mu, s = math.log(p["mean"]) - s2 / 2, math.sqrt(s2)
        return lambda rng, n: rng.lognormal(mu, s, n)
    if d == "gamma":
        if p["mean"] <= 0 or p["cv"] <= 0:
            raise ValueError("gamma: mean e cv devem ser > 0")
        shape, scale = 1 / p["cv"] ** 2, p["mean"] * p["cv"] ** 2
        return lambda rng, n: rng.gamma(shape, scale, n)
    if d == "weibull":
        if p["shape"] <= 0 or p["scale"] <= 0:
            raise ValueError("weibull: shape e scale devem ser > 0")
        return lambda rng, n: p["scale"] * rng.weibull(p["shape"], n)
    if d == "erlang":
        k = int(p["k"])
        if k < 1 or k != p["k"] or p["mean"] <= 0:
            raise ValueError("erlang: k inteiro >= 1 e mean > 0")
        return lambda rng, n: rng.gamma(k, p["mean"] / k, n)
    if d == "normal":
        if p["mean"] <= 0 or p["sd"] <= 0:
            raise ValueError("normal: mean e sd devem ser > 0")

        def normal_truncated(rng, n):
            x = rng.normal(p["mean"], p["sd"], n)
            for _ in range(MAX_TRUNCATION_ROUNDS):
                bad = x <= 0
                if not bad.any():
                    return x
                x[bad] = rng.normal(p["mean"], p["sd"], int(bad.sum()))
            raise ValueError("normal: parâmetros geram quase só valores <= 0")

        return normal_truncated
    if d == "triangular":
        if not (0 <= p["low"] <= p["mode"] <= p["high"] and p["low"] < p["high"]):
            raise ValueError("triangular: 0 <= low <= mode <= high e low < high")
        return lambda rng, n: rng.triangular(p["low"], p["mode"], p["high"], n)
    if d == "uniform":
        if not (0 <= p["low"] < p["high"]):
            raise ValueError("uniform: 0 <= low < high")
        return lambda rng, n: rng.uniform(p["low"], p["high"], n)
    if d == "beta":
        if not (0 <= p["low"] < p["high"]) or p["a"] <= 0 or p["b"] <= 0:
            raise ValueError("beta: 0 <= low < high, a > 0, b > 0")
        return lambda rng, n: p["low"] + (p["high"] - p["low"]) * rng.beta(p["a"], p["b"], n)
    raise ValueError(d)  # inalcançável


def describe(spec: DistSpec, n: int = 200_000, seed: int = 0) -> dict:
    x = build_sampler(spec)(np.random.default_rng(seed), n)
    return {"mean": float(x.mean()), "cv": float(x.std(ddof=1) / x.mean())}


def spec_pdf(spec: DistSpec) -> Callable[[np.ndarray], np.ndarray]:
    """Densidade de probabilidade da especificação (para desenhar curvas)."""
    from scipy import stats

    p = _check(spec)
    build_sampler(spec)  # valida domínio
    d = spec.dist
    if d == "expon":
        return stats.expon(0, p["mean"]).pdf
    if d == "lognormal":
        s2 = math.log(1 + p["cv"] ** 2)
        return stats.lognorm(math.sqrt(s2), 0, p["mean"] / math.sqrt(1 + p["cv"] ** 2)).pdf
    if d == "gamma":
        return stats.gamma(1 / p["cv"] ** 2, 0, p["mean"] * p["cv"] ** 2).pdf
    if d == "weibull":
        return stats.weibull_min(p["shape"], 0, p["scale"]).pdf
    if d == "erlang":
        return stats.gamma(int(p["k"]), 0, p["mean"] / int(p["k"])).pdf
    if d == "normal":
        return stats.norm(p["mean"], p["sd"]).pdf
    if d == "triangular":
        span = p["high"] - p["low"]
        return stats.triang((p["mode"] - p["low"]) / span, p["low"], span).pdf
    if d == "uniform":
        return stats.uniform(p["low"], p["high"] - p["low"]).pdf
    return stats.beta(p["a"], p["b"], p["low"], p["high"] - p["low"]).pdf  # beta

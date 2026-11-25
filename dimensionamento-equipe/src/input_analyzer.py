"""Analisador de entrada (estilo Arena Input Analyzer).

Ajusta distribuições candidatas a durações positivas e ranqueia por AIC. Mostra
também BIC, estatística KS e erro quadrático. Com amostras grandes o p-valor do KS
perde sentido (e os parâmetros foram estimados dos mesmos dados): é só informativo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

import numpy as np
from matplotlib.figure import Figure
from scipy import stats

from .distributions import DistSpec

CANDIDATES = ("expon", "gamma", "weibull", "lognormal", "erlang", "normal", "beta", "triangular", "uniform")
EDGE_PAD = 0.01  # folga relativa nos limites de beta/triangular/uniforme


@dataclass(frozen=True)
class FitResult:
    name: str
    spec: DistSpec
    aic: float
    bic: float
    ks_stat: float
    ks_p: float
    sq_error: float
    rank: int = 0
    pdf: Callable = field(default=None, repr=False, compare=False)


def clean_values(values: Iterable) -> tuple[np.ndarray, dict]:
    kept, rep = [], {"kept": 0, "dropped_empty": 0, "dropped_non_numeric": 0, "dropped_nonpositive": 0}
    for v in values:
        if v is None or (isinstance(v, str) and not v.strip()):
            rep["dropped_empty"] += 1
            continue
        try:
            x = float(v.strip().replace(",", ".")) if isinstance(v, str) else float(v)
        except (TypeError, ValueError):
            rep["dropped_non_numeric"] += 1
            continue
        if math.isnan(x):
            rep["dropped_empty"] += 1
        elif math.isinf(x):
            rep["dropped_non_numeric"] += 1
        elif x <= 0:
            rep["dropped_nonpositive"] += 1
        else:
            kept.append(x)
    rep["kept"] = len(kept)
    return np.asarray(kept, dtype=float), rep


def _builders(v: np.ndarray) -> dict[str, Callable[[], tuple]]:
    """nome -> função que ajusta e devolve (spec, distribuição congelada, nº de parâmetros).

    Cada ajuste é calculado só quando pedido, para uma falha isolada não derrubar o ranking.
    """
    lo_data, hi_data = float(v.min()), float(v.max())
    span_data = hi_data - lo_data
    low = max(0.0, lo_data - EDGE_PAD * span_data)
    high = hi_data + EDGE_PAD * span_data
    width = high - low
    mean = float(v.mean())

    def expon():
        _, scale = stats.expon.fit(v, floc=0)
        return DistSpec("expon", {"mean": scale}), stats.expon(0, scale), 1

    def gamma():
        a, _, scale = stats.gamma.fit(v, floc=0)
        return DistSpec("gamma", {"mean": a * scale, "cv": 1 / math.sqrt(a)}), stats.gamma(a, 0, scale), 2

    def weibull():
        c, _, scale = stats.weibull_min.fit(v, floc=0)
        return DistSpec("weibull", {"shape": c, "scale": scale}), stats.weibull_min(c, 0, scale), 2

    def lognormal():
        s, _, scale = stats.lognorm.fit(v, floc=0)
        lm = scale * math.exp(s * s / 2)
        return DistSpec("lognormal", {"mean": lm, "cv": math.sqrt(math.expm1(s * s))}), stats.lognorm(s, 0, scale), 2

    def erlang():
        k = max(1, int(round((mean / float(v.std())) ** 2)))  # forma inteira pelo método dos momentos
        return DistSpec("erlang", {"k": k, "mean": mean}), stats.gamma(k, 0, mean / k), 2

    def normal():
        mu, sd = stats.norm.fit(v)
        return DistSpec("normal", {"mean": mu, "sd": sd}), stats.norm(mu, sd), 2

    def beta():
        u = (v - low) / width
        ab, bb, _, _ = stats.beta.fit(u, floc=0, fscale=1)
        return DistSpec("beta", {"low": low, "high": high, "a": ab, "b": bb}), stats.beta(ab, bb, low, width), 4

    def triangular():
        ct, _, _ = stats.triang.fit(v, floc=low, fscale=width)
        return DistSpec("triangular", {"low": low, "mode": low + ct * width, "high": high}), stats.triang(ct, low, width), 3

    def uniform():
        return DistSpec("uniform", {"low": low, "high": high}), stats.uniform(low, width), 2

    return {
        "expon": expon, "gamma": gamma, "weibull": weibull, "lognormal": lognormal, "erlang": erlang,
        "normal": normal, "beta": beta, "triangular": triangular, "uniform": uniform,
    }

def _sq_error(v: np.ndarray, dist) -> float:
    n_bins = int(min(60, max(10, math.sqrt(len(v)))))
    edges = np.linspace(v.min(), v.max(), n_bins + 1)
    obs = np.histogram(v, bins=edges)[0] / len(v)
    exp = np.diff(dist.cdf(edges))
    return float(np.mean((obs - exp) ** 2))


def fit_distributions(values: np.ndarray, candidates: Sequence[str] = CANDIDATES, min_points: int = 30) -> list[FitResult]:
    v = np.asarray(values, dtype=float)
    if len(v) < min_points:
        raise ValueError(f"poucos pontos: {len(v)} (mínimo {min_points})")
    if not np.all(np.isfinite(v)) or (v <= 0).any():
        raise ValueError("valores devem ser finitos e positivos (use clean_values antes)")
    if float(np.std(v)) == 0.0:
        raise ValueError("variância zero: todos os valores são iguais")
    unknown = set(candidates) - set(CANDIDATES)
    if unknown:
        raise ValueError(f"candidatas desconhecidas: {sorted(unknown)}")

    builders = _builders(v)
    n = len(v)
    results = []
    for name in candidates:
        try:
            spec, dist, k = builders[name]()
            ll = float(np.sum(dist.logpdf(v)))
            if not math.isfinite(ll):
                continue
            ks = stats.kstest(v, dist.cdf)
            results.append(
                FitResult(
                    name=name,
                    spec=spec,
                    aic=2 * k - 2 * ll,
                    bic=k * math.log(n) - 2 * ll,
                    ks_stat=float(ks.statistic),
                    ks_p=float(ks.pvalue),
                    sq_error=_sq_error(v, dist),
                    pdf=dist.pdf,
                )
            )
        except Exception:  # um ajuste que falha não derruba o ranking
            continue
    if not results:
        raise ValueError("nenhuma distribuição pôde ser ajustada a esta amostra")
    results.sort(key=lambda r: (r.aic, r.ks_stat))
    return [FitResult(**{**r.__dict__, "rank": i + 1}) for i, r in enumerate(results)]


def histogram_with_fits(values: np.ndarray, fits: Sequence[FitResult], bins: int = 40) -> Figure:
    v = np.asarray(values, dtype=float)
    top = float(np.percentile(v, 99.5))  # corta a cauda extrema só no desenho
    fig = Figure(figsize=(9, 3.8))
    ax = fig.subplots()
    ax.hist(v[v <= top], bins=bins, density=True, color="#cccccc", label="dados / data")
    xs = np.linspace(max(v.min(), 1e-9), top, 400)
    for f in fits:
        if f.pdf is not None:
            ax.plot(xs, f.pdf(xs), label=f"{f.rank}. {f.name}")
    ax.set_xlabel("segundos / seconds")
    ax.set_ylabel("densidade / density")
    ax.legend()
    fig.tight_layout()
    return fig


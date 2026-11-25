"""Previsão de chamadas por hora: regra simples (4 semanas) e Poisson GLM."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from pandas.tseries.holiday import USFederalHolidayCalendar

TZ = "America/New_York"
FORMULA = "calls ~ C(dow) * C(hour) + holiday + trend"


def us_federal_holidays(start: str, end: str) -> set[date]:
    days = USFederalHolidayCalendar().holidays(start=start, end=end)
    return {d.date() for d in days}


def baseline_same_hour_4w(series: pd.Series) -> pd.Series:
    """Média das observações da mesma hora com defasagem de 7, 14, 21 e 28 dias."""
    lags = [series.shift(24 * 7 * k) for k in range(1, 5)]
    out = pd.concat(lags, axis=1).mean(axis=1, skipna=False)
    out.name = "baseline"
    return out


def build_features(
    index: pd.DatetimeIndex,
    tz: str = TZ,
    holidays: Iterable[date] = (),
    origin: pd.Timestamp | None = None,
) -> pd.DataFrame:
    local = index.tz_convert(tz)
    origin = index[0] if origin is None else origin
    hol = set(holidays)
    return pd.DataFrame(
        {
            "hour": local.hour,
            "dow": local.day_of_week,
            "holiday": [int(d in hol) for d in local.date],
            "trend": (index - origin) / pd.Timedelta(days=365),
        },
        index=index,
    )


@dataclass
class FittedModel:
    result: object
    tz: str
    holidays: frozenset
    origin: pd.Timestamp


def fit_poisson(train: pd.Series, holidays: Iterable[date] = (), tz: str = TZ) -> FittedModel:
    origin = train.index[0]
    df = build_features(train.index, tz, holidays, origin)
    df["calls"] = train.to_numpy()
    res = smf.glm(FORMULA, data=df, family=sm.families.Poisson()).fit()
    return FittedModel(res, tz, frozenset(holidays), origin)


def predict(model: FittedModel, index: pd.DatetimeIndex) -> pd.Series:
    df = build_features(index, model.tz, model.holidays, model.origin)
    return pd.Series(np.asarray(model.result.predict(df)), index=index, name="forecast")


def wape(actual: pd.Series, pred: pd.Series) -> float:
    return float((actual - pred).abs().sum() / actual.abs().sum())


def mape_details(actual: pd.Series, pred: pd.Series) -> tuple[float, int]:
    mask = actual != 0
    value = float(((actual[mask] - pred[mask]).abs() / actual[mask]).mean())
    return value, int((~mask).sum())


def mape(actual: pd.Series, pred: pd.Series) -> float:
    return mape_details(actual, pred)[0]


def _score(series: pd.Series, test: pd.Series, pred: pd.Series) -> dict:
    """Mesma métrica e mesmo conjunto de horas para o modelo e para a regra simples."""
    base = baseline_same_hour_4w(series).reindex(test.index)
    ok = base.notna()
    actual, pred, base = test[ok], pred[ok], base[ok]
    m_model, ignored = mape_details(actual, pred)
    m_base, _ = mape_details(actual, base)
    w_model, w_base = wape(actual, pred), wape(actual, base)
    return {
        "wape_model": w_model,
        "wape_baseline": w_base,
        "mape_model": m_model,
        "mape_baseline": m_base,
        "mape_ignored_hours": ignored,
        "n_hours": int(len(actual)),
        "gain_wape_rel": (w_base - w_model) / w_base,
        "forecast": pred,
    }


def evaluate(
    series: pd.Series,
    train_year: int,
    test_year: int,
    holidays: Iterable[date] | None = None,
    tz: str = TZ,
) -> dict:
    """Ajuste único no ano de treino; mede só no ano de teste."""
    year = series.index.tz_convert(tz).year
    train, test = series[year == train_year], series[year == test_year]
    if holidays is None:
        holidays = us_federal_holidays(f"{train_year}-01-01", f"{test_year}-12-31")
    model = fit_poisson(train, holidays, tz)
    out = _score(series, test, predict(model, test.index))
    out["model"] = model
    return out


def evaluate_walk_forward(
    series: pd.Series,
    train_year: int,
    test_year: int,
    holidays: Iterable[date] | None = None,
    tz: str = TZ,
) -> dict:
    """Reajusta o modelo no início de cada mês do ano de teste, usando só dados anteriores."""
    local = series.index.tz_convert(tz)
    test = series[local.year == test_year]
    if holidays is None:
        holidays = us_federal_holidays(f"{train_year}-01-01", f"{test_year}-12-31")
    months = sorted(set(test.index.tz_convert(tz).month))
    parts = []
    for m in months:
        start = pd.Timestamp(year=test_year, month=m, day=1, tz=tz).tz_convert("UTC")
        past = series[(series.index.tz_convert(tz).year >= train_year) & (series.index < start)]
        month_idx = test.index[test.index.tz_convert(tz).month == m]
        parts.append(predict(fit_poisson(past, holidays, tz), month_idx))
    out = _score(series, test, pd.concat(parts))
    out["refits"] = len(months)
    return out

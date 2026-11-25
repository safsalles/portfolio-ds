"""Monitor intraday: previsto x realizado e alerta por webhook do Slack."""
from __future__ import annotations

import pandas as pd
import requests


def compare_intraday(forecast: pd.Series, actual: pd.Series) -> pd.DataFrame:
    df = pd.concat({"forecast": forecast, "actual": actual}, axis=1, join="inner")
    df["deviation"] = (df["actual"] - df["forecast"]) / df["forecast"].clip(lower=1)
    df.index.name = "hour"
    return df.reset_index()


def find_alerts(df: pd.DataFrame, threshold: float, min_calls: int = 20) -> pd.DataFrame:
    mask = (df["deviation"].abs() > threshold) & (df["forecast"] >= min_calls)
    return df[mask].reset_index(drop=True)


def format_alert(row: pd.Series) -> str:
    return (
        f"[TESTE] Desvio em {row['hour']}: previsto {row['forecast']:.0f}, "
        f"realizado {row['actual']:.0f} ({row['deviation']:+.0%})"
    )


def send_slack_alert(webhook_url: str, text: str, post=requests.post) -> bool:
    try:
        resp = post(webhook_url, json={"text": text}, timeout=10)
        return getattr(resp, "status_code", None) == 200
    except Exception:
        return False


def run_monitor(forecast, actual, threshold: float, webhook_url: str | None, post=requests.post) -> dict:
    alerts = find_alerts(compare_intraday(forecast, actual), threshold)
    sent = 0
    if webhook_url:
        sent = sum(send_slack_alert(webhook_url, format_alert(r), post=post) for _, r in alerts.iterrows())
    return {"alerts": int(len(alerts)), "sent": int(sent)}

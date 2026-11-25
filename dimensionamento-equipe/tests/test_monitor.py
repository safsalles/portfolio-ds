import pandas as pd
import pytest
import requests

from src.monitor import (
    compare_intraday,
    find_alerts,
    format_alert,
    run_monitor,
    send_slack_alert,
)


def series(values):
    idx = pd.date_range("2023-03-01", periods=len(values), freq="h", tz="UTC")
    return pd.Series(values, index=idx, dtype=float)


class FakeResp:
    def __init__(self, code):
        self.status_code = code


def test_alert_above_threshold_only():
    df = compare_intraday(series([100, 100, 100]), series([100, 140, 60]))
    alerts = find_alerts(df, 0.30)
    assert list(alerts["actual"]) == [140.0, 60.0]


def test_min_calls_suppresses_noise():
    df = compare_intraday(series([5, 100]), series([15, 100]))
    assert find_alerts(df, 0.30, min_calls=20).empty


def test_slack_payload_and_url():
    seen = {}

    def post(url, json=None, timeout=None):
        seen["url"], seen["json"] = url, json
        return FakeResp(200)

    assert send_slack_alert("https://hooks.test/x", "oi", post=post) is True
    assert seen == {"url": "https://hooks.test/x", "json": {"text": "oi"}}


def test_webhook_failure_does_not_raise():
    def boom(*a, **k):
        raise requests.ConnectionError("down")

    assert send_slack_alert("https://hooks.test/x", "oi", post=boom) is False
    assert send_slack_alert("https://hooks.test/x", "oi", post=lambda *a, **k: FakeResp(500)) is False


def test_no_webhook_url_dry_run():
    called = []
    r = run_monitor(series([100, 100]), series([100, 200]), 0.30, None, post=lambda *a, **k: called.append(1))
    assert r == {"alerts": 1, "sent": 0} and not called


def test_run_monitor_sends_each_alert():
    r = run_monitor(series([100, 100]), series([200, 200]), 0.30, "https://hooks.test/x", post=lambda *a, **k: FakeResp(200))
    assert r == {"alerts": 2, "sent": 2}


def test_format_alert_mentions_numbers():
    df = compare_intraday(series([100]), series([150]))
    txt = format_alert(df.iloc[0])
    assert "100" in txt and "150" in txt

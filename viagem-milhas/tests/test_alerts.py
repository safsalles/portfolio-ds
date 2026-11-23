import subprocess

from verificador import alerts
from verificador.alerts import notify, price_alerts


def test_drop_of_5_percent_alerts():
    messages = price_alerts(19152, 18194, 5.0, 18000)

    assert len(messages) == 1
    assert "caiu" in messages[0].lower()


def test_drop_of_4_percent_is_silent():
    assert price_alerts(19152, 18400, 5.0, 18000) == []


def test_below_target_alerts_even_on_first_run():
    messages = price_alerts(None, 17900, 5.0, 18000)

    assert len(messages) == 1
    assert "alvo" in messages[0].lower()


def test_first_run_above_target_is_silent():
    assert price_alerts(None, 19152, 5.0, 18000) == []


def test_increase_is_silent():
    assert price_alerts(19152, 20000, 5.0, 18000) == []


def test_notify_writes_log_even_if_toast_fails(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("sem powershell")

    monkeypatch.setattr(alerts.subprocess, "run", boom)
    log = tmp_path / "data" / "alerts.log"

    notify("Titulo", "Mensagem de teste", str(log))

    content = log.read_text(encoding="utf-8")
    assert "Titulo" in content and "Mensagem de teste" in content
    assert subprocess is not None


def test_still_below_target_next_day_is_silent():
    assert price_alerts(17900, 17850, 5.0, 18000) == []


def test_crossing_below_target_alerts():
    assert len(price_alerts(18500, 17900, 5.0, 18000)) == 1

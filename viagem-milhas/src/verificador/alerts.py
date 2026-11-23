import os
import subprocess
from datetime import datetime


def price_alerts(previous: float | None, current: float, drop_pct: float, target_brl: float) -> list[str]:
    messages: list[str] = []
    if previous is not None and previous > 0:
        drop = (previous - current) / previous * 100
        if drop >= drop_pct:
            messages.append(
                f"Preço caiu {drop:.1f}%: de R$ {previous:,.2f} para R$ {current:,.2f}."
            )
    crossed_below = previous is None or previous >= target_brl  # so avisa na travessia, nao todo dia
    if current < target_brl and crossed_below:
        messages.append(f"Preço abaixo do valor-alvo (R$ {target_brl:,.2f}): agora R$ {current:,.2f}.")
    return messages


def _toast(title: str, message: str) -> None:
    safe_title = title.replace("'", "''")
    safe_message = message.replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Information; "
        "$n.Visible = $true; "
        f"$n.ShowBalloonTip(10000, '{safe_title}', '{safe_message}', 'Info'); "
        "Start-Sleep -Seconds 11; $n.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], timeout=30, check=False)


def notify(title: str, message: str, log_path: str) -> None:
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {title}: {message}\n")
    try:
        _toast(title, message)
    except Exception:
        pass  # o registro em arquivo ja foi gravado; aviso na tela e' extra

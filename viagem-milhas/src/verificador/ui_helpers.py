"""Pequenas funcoes de apresentacao usadas pela interface (sem dependencia do Streamlit)."""
from verificador.snapshots import SnapshotMeta


def format_brl(value: float | None) -> str:
    if value is None:
        return "—"
    text = f"{value:,.2f}"  # 1,234.50 -> troca para o padrao brasileiro 1.234,50
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def snapshot_label(meta: SnapshotMeta) -> str:
    when = meta.saved_at.strftime("%d/%m/%Y %H:%M")
    best = f"melhor {format_brl(meta.best_total_brl)}" if meta.best_total_brl is not None else "nenhuma passa nas regras"
    count = f"{meta.n_offers} oferta" + ("" if meta.n_offers == 1 else "s")
    return f"{when} · {meta.source} · {best} · {count}"


def delta_text(delta: tuple[float, float] | None) -> str:
    if delta is None:
        return "sem como comparar"
    value, pct = delta
    if value == 0:
        return "mesmo preço"
    amount = format_brl(abs(value))
    pct_text = f"{abs(pct):.1f}".replace(".", ",")
    if value < 0:
        return f"{amount} mais barato (−{pct_text}%)"
    return f"{amount} mais caro (+{pct_text}%)"

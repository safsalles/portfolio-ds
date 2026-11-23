import argparse

from verificador.calculator import breakeven_milheiro
from verificador.history import latest_ok
from verificador.other_sources import DEFAULT_PATH, latest_by_source, load_checks


def build_report(history_path: str, others_path: str) -> str:
    lines: list[str] = []
    cash: list[tuple[float, str]] = []

    google = latest_ok(history_path)
    if google:
        lines.append(f"Google Voos (automático): R$ {google.total_price_brl:,.2f} em {google.date}")
        cash.append((google.total_price_brl, "google voos"))

    latest = latest_by_source(load_checks(others_path))
    for source, c in sorted(latest.items()):
        parts = []
        if c.price_brl is not None:
            parts.append(f"R$ {c.price_brl:,.2f}")
            cash.append((c.price_brl, source))
        if c.miles is not None:
            taxes = f" + R$ {c.taxes_brl:,.2f} de taxas" if c.taxes_brl is not None else ""
            parts.append(f"{c.miles:,} milhas{taxes}")
        note = f" ({c.note})" if c.note else ""
        lines.append(f"{source}: {' | '.join(parts) or 'sem valor'} em {c.date}{note}")

    if not lines:
        return "Sem dados ainda."

    if cash:
        best_price, best_source = min(cash)
        lines.append(f"Menor preço em dinheiro: R$ {best_price:,.2f} ({best_source})")
        for source, c in sorted(latest.items()):
            if c.miles:
                be = breakeven_milheiro(best_price, c.miles, c.taxes_brl or 0.0)
                lines.append(
                    f"Equilíbrio do milheiro ({source}): R$ {be:.2f} — abaixo disso as milhas ganham do dinheiro"
                )
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="Relatório: Google Voos + outras fontes")
    p.add_argument("--history", default="data/history.csv")
    p.add_argument("--others", default=DEFAULT_PATH)
    a = p.parse_args()
    print(build_report(a.history, a.others))


if __name__ == "__main__":
    main()

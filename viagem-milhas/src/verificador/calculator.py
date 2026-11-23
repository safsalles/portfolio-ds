import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class Comparison:
    miles_cost_brl: float
    cash_brl: float
    miles_win: bool
    savings_brl: float  # positivo = milhas ganham


def _check_miles(miles: int) -> None:
    if miles <= 0:
        raise ValueError("miles deve ser maior que zero")


def breakeven_milheiro(cash_brl: float, miles: int, taxes_brl: float) -> float:
    _check_miles(miles)
    return (cash_brl - taxes_brl) / (miles / 1000)


def compare(cash_brl: float, miles: int, milheiro_brl: float, taxes_brl: float) -> Comparison:
    _check_miles(miles)
    miles_cost = miles / 1000 * milheiro_brl + taxes_brl
    savings = cash_brl - miles_cost
    return Comparison(miles_cost, cash_brl, savings > 0, savings)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara dinheiro x milhas")
    parser.add_argument("--cash", type=float, required=True, help="preco em dinheiro (R$)")
    parser.add_argument("--miles", type=int, required=True, help="milhas necessarias")
    parser.add_argument("--milheiro", type=float, required=True, help="preco do milheiro (R$)")
    parser.add_argument("--taxes", type=float, default=0.0, help="taxas em R$")
    args = parser.parse_args()

    result = compare(args.cash, args.miles, args.milheiro, args.taxes)
    equilibrio = breakeven_milheiro(args.cash, args.miles, args.taxes)
    print(f"Dinheiro: R$ {result.cash_brl:,.2f}")
    print(f"Milhas:   R$ {result.miles_cost_brl:,.2f} (milheiro R$ {args.milheiro:.2f} + taxas)")
    print(f"Equilibrio: milheiro de R$ {equilibrio:.2f}")
    if result.miles_win:
        print(f"Resultado: milhas ganham, economia de R$ {result.savings_brl:,.2f}")
    else:
        print(f"Resultado: dinheiro ganha, milhas custam R$ {-result.savings_brl:,.2f} a mais")


if __name__ == "__main__":
    main()

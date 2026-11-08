"""Partes da linha de comando usadas pelos dois programas."""

import argparse
from math import isfinite

from memga.radar import interactive


def tau_argument(text):
    try:
        tau = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} não é um número") from None
    if not (isfinite(tau) and tau > 0):
        raise argparse.ArgumentTypeError("o tau precisa ser um número finito maior que 0")
    return tau


def finish_with_radar(args, draw):
    """Salva o gráfico se `--radar` foi pedido e abre a janela quando há alguém no terminal."""
    show = interactive() and not args.no_plot
    if args.radar:
        print(f"\nGráfico de radar salvo em {args.radar}")
    if show:
        print("\nO gráfico de radar abriu em outra janela. Feche a janela para terminar.")
    if args.radar or show:
        draw(args.radar, show)

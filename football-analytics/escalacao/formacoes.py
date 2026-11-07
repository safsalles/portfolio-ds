"""Formações: os atalhos, como 4-4-2, e as vagas por posição que cada uma pede."""

import numpy as np

FREE_WORDS = {"", "livre", "free"}

# Para mudar um atalho ou criar outro, basta editar esta tabela.
PRESETS = {
    "4-4-2": {"ZAG": 2, "LE": 1, "LD": 1, "VOL": 2, "MEI": 2, "ATA": 2},
    "4-3-3": {"ZAG": 2, "LE": 1, "LD": 1, "VOL": 1, "MEI": 2, "ATA": 3},
    "4-2-3-1": {"ZAG": 2, "LE": 1, "LD": 1, "VOL": 2, "MEI": 3, "ATA": 1},
    "4-1-4-1": {"ZAG": 2, "LE": 1, "LD": 1, "VOL": 1, "MEI": 4, "ATA": 1},
    "3-5-2": {"ZAG": 3, "VOL": 2, "MEI": 3, "ATA": 2},
    "3-4-3": {"ZAG": 3, "VOL": 2, "MEI": 2, "ATA": 3},
    "3-6-1": {"ZAG": 3, "VOL": 3, "MEI": 3, "ATA": 1},
    "5-3-2": {"ZAG": 3, "LE": 1, "LD": 1, "VOL": 2, "MEI": 1, "ATA": 2},
    "5-4-1": {"ZAG": 3, "LE": 1, "LD": 1, "VOL": 2, "MEI": 2, "ATA": 1},
}


class FormationError(ValueError):
    """A formação digitada não pode ser montada com estes dados."""


def _parse_custom(text):
    quotas = {}
    for part in text.split(","):
        position, separator, amount = part.partition("=")
        position = position.strip().upper()
        if not separator or not position or not amount.strip().isdigit():
            raise FormationError(
                f"Não entendi {text!r}. Use um atalho ({', '.join(PRESETS)}), "
                "'livre' ou o formato zag=2,le=1,ld=1,vol=2,mei=2,ata=2."
            )
        if position in quotas:
            raise FormationError(f"A posição {position} apareceu duas vezes.")
        quotas[position] = int(amount)
    return quotas


def parse_formation(text, positions, team_size=10):
    """Devolve as quotas por posição, ou None para o time livre."""
    text = text.strip()
    if text.lower() in FREE_WORDS:
        return None

    if text.isdigit():
        text = "-".join(text)  # aceita 442 no lugar de 4-4-2
    quotas = dict(PRESETS[text]) if text in PRESETS else _parse_custom(text)

    names, counts = np.unique(positions, return_counts=True)
    available = dict(zip(names.tolist(), counts.tolist()))
    for position, quota in quotas.items():
        if quota > available.get(position, 0):
            raise FormationError(
                f"A formação pede {quota} de {position}, mas os dados têm "
                f"{available.get(position, 0)}."
            )

    total = sum(quotas.values())
    if total != team_size:
        raise FormationError(f"A formação soma {total} jogadores, e o time precisa de {team_size}.")
    return quotas

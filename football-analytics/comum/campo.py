"""O time em campo, no terminal, e o radar com os nomes dos critérios em português."""

from mem.radar import plot_radar as draw_radar

CRITERIA_NAMES = {
    "Tackles": "Desarmes", "Interception": "Interceptações", "Fouled": "Faltas sofridas",
    "Fouls": "Poucas faltas", "Yellow": "Poucos amarelos", "Red": "Poucos vermelhos",
    "Clearences": "Bolas afastadas", "ShotsW": "Chutes certos", "GolsA": "Gols na área",
    "GolsFA": "Gols fora da área", "DribblesSuccessful": "Dribles certos",
    "PossLost": "Poucas perdas", "AerialWon": "Disputas aéreas", "AccLB": "Passes longos",
    "AccSP": "Passes curtos", "KPLong": "Passes-chave longos", "KPShort": "Passes-chave curtos",
    "AssistsTotal": "Assistências",
}
RADAR_NOTE = "Desempenho por critério, normalizado e ajustado pela posição de cada jogador, como na nota."

# Linhas do campo, do ataque para a defesa e da esquerda para a direita.
PITCH_ROWS = (("ATA",), ("MEI",), ("VOL",), ("LE", "ZAG", "LD"))
MAX_PER_PITCH_ROW = 4


def plot_radar(criteria, panels, path=None, show=False, note=RADAR_NOTE):
    """O radar do método, com os nomes dos critérios em português."""
    draw_radar([CRITERIA_NAMES.get(name, name) for name in criteria], panels, path, show, note)


def spread(names, width):
    """Distribui os nomes de uma linha do campo, com a mesma folga entre eles."""
    gap, extra = divmod(width - sum(len(name) for name in names), len(names) + 1)
    line = "".join(" " * (gap + (i < extra)) + name for i, name in enumerate(names))
    return line.ljust(width)


def pitch_lines(dataset, strengths, team):
    """Desenha o time em campo. Com outras posições nos dados, não há o que desenhar."""
    known = {position for row in PITCH_ROWS for position in row}
    if any(dataset.positions[player] not in known for player in team):
        return []

    rows = []
    for row in PITCH_ROWS:
        players = sorted(
            (player for player in team if dataset.positions[player] in row),
            key=lambda player: (row.index(dataset.positions[player]), -strengths[player]),
        )
        for start in range(0, len(players), MAX_PER_PITCH_ROW):
            rows.append([dataset.players[p] for p in players[start:start + MAX_PER_PITCH_ROW]])
    if dataset.goalkeeper:
        rows.append([dataset.goalkeeper["name"]])

    width = max(sum(len(name) + 2 for name in row) + 2 for row in rows)
    goal_line = "+" + "[     ]".center(width, "-") + "+"
    blank = "|" + " " * width + "|"

    lines = [goal_line, blank]
    for index, row in enumerate(rows):
        if index == len(rows) // 2:
            lines += ["|" + "o".center(width, "-") + "|", blank]
        lines += ["|" + spread(row, width) + "|", blank]
    return [*lines, goal_line]

"""Os goleiros ficam fora da nota do time e são ordenados à parte, pelos critérios atingidos."""

from pathlib import Path

import numpy as np

from comum.arquivos import DEFAULT_DATA_DIR, DEFAULT_MIN_MINUTES, number, read_csv, require_columns

GOALKEEPER_CRITERIA = ("save_rate", "long_pass_rate", "clearances_per_90")


def rank_goalkeepers(folder=DEFAULT_DATA_DIR, min_minutes=DEFAULT_MIN_MINUTES):
    """Ordena os goleiros pelos critérios atingidos. O arquivo é opcional.

    Atingir um critério é ficar entre os 20% melhores goleiros naquele critério. O
    desempate é o aproveitamento de defesas.
    """
    path = Path(folder) / "goalkeepers.csv"
    if not path.is_file():
        return []

    columns, rows = read_csv(path)
    required = [
        "player", "team", "minutes", "saves", "goals_conceded",
        "long_passes_accurate", "long_passes_inaccurate", "clearances",
    ]
    require_columns(columns, required, "goalkeepers.csv")

    keepers = []
    for row in rows:
        stats = {name: number(row[name], f"{name} de {row['player']}") for name in required[2:]}
        shots_on_target = stats["saves"] + stats["goals_conceded"]
        long_passes = stats["long_passes_accurate"] + stats["long_passes_inaccurate"]
        if stats["minutes"] < min_minutes or shots_on_target == 0:
            continue
        keepers.append({
            "name": f"{row['player'].strip()} ({row['team'].strip()})",
            "team": row["team"].strip(),
            "minutes": stats["minutes"],
            "save_rate": stats["saves"] / shots_on_target,
            "long_pass_rate": stats["long_passes_accurate"] / long_passes if long_passes else 0.0,
            "clearances_per_90": stats["clearances"] / stats["minutes"] * 90,
            "hits": 0,
        })

    if keepers:
        for criterion in GOALKEEPER_CRITERIA:
            cut = np.quantile([keeper[criterion] for keeper in keepers], 0.8)
            for keeper in keepers:
                keeper["hits"] += keeper[criterion] >= cut
    return sorted(keepers, key=lambda keeper: (-keeper["hits"], -keeper["save_rate"]))

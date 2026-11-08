"""Gera os dados fictícios do exemplo grande: 300 candidatos para uma equipe de projeto.

Para refazer os arquivos de data/: python gerar_dados.py

Os dados são sorteados com semente fixa, então rodar de novo dá os mesmos arquivos. Cada
cargo tem um perfil próprio (analistas mais fortes em dados, engenheiros em programação,
gestores em liderança e negociação), e os critérios andam juntos ou em sentidos opostos,
como na vida real: quem programa muito bem nem sempre negocia bem. É isso que dá sentido
à complementação calculada dos dados.
"""

import csv
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent / "data"
SEED = 2026
CRITERIA = (
    "sql", "estatistica", "visualizacao", "programacao",
    "comunicacao", "lideranca", "negociacao", "organizacao",
)
SPREAD = 1.5  # desvio-padrão de cada critério, na escala de 0 a 10

# Quantos candidatos de cada cargo e a média de cada critério, na ordem de CRITERIA.
ROLES = {
    "analista": (150, (7.5, 7.0, 7.0, 5.5, 5.5, 4.0, 4.0, 6.0)),
    "engenheiro": (90, (6.5, 5.5, 4.5, 8.0, 4.5, 4.0, 3.5, 6.0)),
    "gestor": (60, (4.0, 4.5, 5.5, 3.5, 7.5, 7.5, 7.0, 7.0)),
}

# Carga de cada critério em dois traços: um técnico e um de relacionamento. A correlação
# entre dois critérios sai do quanto eles dependem dos mesmos traços, com sinal: os
# critérios técnicos andam juntos e vão no sentido oposto ao da negociação e da liderança.
TECHNICAL = np.array([0.7, 0.6, 0.4, 0.7, -0.2, -0.3, -0.3, 0.2])
SOCIAL = np.array([0.0, 0.0, 0.4, -0.2, 0.7, 0.6, 0.6, 0.3])
# Peso de cada traço em cada cargo: entre gestores o traço técnico pesa menos, e assim
# cada cargo fica com uma matriz de correlação própria.
TRAITS = {"analista": (1.0, 0.8), "engenheiro": (1.0, 0.6), "gestor": (0.6, 1.0)}


def correlation(role):
    """Matriz de correlação de um cargo, montada a partir das cargas nos dois traços."""
    technical, social = TRAITS[role]
    loadings = np.column_stack([technical * TECHNICAL, social * SOCIAL])
    shared = loadings @ loadings.T
    return shared + np.diag(1 - np.diag(shared))


def generate(seed=SEED):
    """Devolve (critérios, candidatos) como listas de dicionários, prontas para o CSV."""
    rng = np.random.default_rng(seed)
    criteria = [{"criterion": name, "direction": 1, "weight": 1.0} for name in CRITERIA]
    candidates = []
    for role, (count, means) in ROLES.items():
        covariance = correlation(role) * SPREAD**2
        sample = np.clip(rng.multivariate_normal(means, covariance, size=count), 0, 10)
        for row in sample:
            number = len(candidates) + 1
            values = {name: float(f"{value:.1f}") for name, value in zip(CRITERIA, row)}
            candidates.append({"alternative": f"P{number:03d}", "group": role, **values})
    return criteria, candidates


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    criteria, candidates = generate()
    DATA_DIR.mkdir(exist_ok=True)
    write_csv(DATA_DIR / "criteria.csv", criteria)
    write_csv(DATA_DIR / "alternatives.csv", candidates)
    print(f"{len(candidates)} candidatos e {len(criteria)} critérios gravados em {DATA_DIR}")


if __name__ == "__main__":
    main()

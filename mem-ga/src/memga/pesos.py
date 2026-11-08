"""Complementação entre critérios e pesos por grupo, calculados a partir dos dados."""

import numpy as np


def complementarity_from_data(values, groups=None):
    """Complementação entre critérios: 1 menos a correlação, em módulo.

    É a medida de conflito do método CRITIC (Diakoulaki et al., 1995). Com grupos, a
    correlação é calculada dentro de cada grupo. Sem isso, ela só mostraria que os grupos
    fazem coisas diferentes, como analistas e gestores.
    """
    centered = np.array(values, float)
    if groups is None:
        groups = np.zeros(len(centered))
    for group in np.unique(groups):
        members = groups == group
        centered[members] -= centered[members].mean(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        correlation = np.corrcoef(centered, rowvar=False)
    return 1 - np.abs(np.nan_to_num(correlation))


def group_weights(values, groups, direction):
    """Peso de cada critério para cada alternativa, conforme o grupo dela.

    Todo critério parte de 1 e ganha o quanto o grupo faz aquilo acima dos outros, em
    desvios-padrão. Os critérios são os mesmos, e só a prioridade muda com o grupo.
    """
    weights = np.ones(values.shape)
    spread = values.std(axis=0)
    spread[spread == 0] = 1
    for group in np.unique(groups):
        members = groups == group
        if members.all():
            continue
        lead = (values[members].mean(axis=0) - values[~members].mean(axis=0)) / spread
        raw = 1 + np.clip(np.where(np.asarray(direction) >= 1, lead, 0), 0, None)
        weights[members] = raw / raw.mean()
    return weights

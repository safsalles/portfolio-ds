"""Roda os modelos de eficiência em cada grupo de posição e grava resultados_dea_2026.csv.

Modelo principal: CCR com restrição de pesos ("restrito"): cada categoria de outputs responde pelo peso
que recebeu no AHP (ahp.py), e o modelo escolhe como dividir dentro dela. Versão leve: cada categoria
responde por pelo menos metade desse peso. O CCR livre fica para comparação.

Amostra: jogadores dos 40 clubes acima da mediana de minutos em 2026 (regra do artigo de 2018).
DEA: totais da temporada, com minutos como input. TOPSIS: taxas por 90, sem minutos.

As variáveis negativas (direção "-") de cada posição são somadas em taxa por 90 e viram um output só,
"menos_erros" = quanto o jogador está melhor que o pior do grupo, vezes os minutos dele:
    y' = (taxa_max - taxa) * minutos / 90
Outputs positivos que podem ser negativos (gols evitados) usam (taxa - taxa_min) * minutos / 90.
É a ideia do artigo de 2018 (inverter o sinal e somar o módulo do menor), aplicada à taxa para não
premiar quem simplesmente jogou menos.
"""
import sys

import numpy as np
import pandas as pd

import ahp
import criterios as c
import dea

BASE = sys.argv[1] if len(sys.argv) > 1 else "../../dados-fotmob/consolidado/br40"
# Variante do input de clube: "log" (padrão: log10 do valor do elenco), "valor" (valor bruto) ou "sem".
# O valor bruto vai de 3 a 225 milhões de euros; como o CCR supõe proporcionalidade, ele esperava que um
# jogador do clube mais barato produzisse 1/75 do que produz um do mais caro, e quase toda a Série B
# virava eficiente. O log mantém a ideia do artigo (clube rico ajuda) com retorno decrescente.
VARIANTE = sys.argv[2] if len(sys.argv) > 2 else "log"
SUFIXO = {"log": "", "valor": "_valor_bruto", "sem": "_sem_clube"}[VARIANTE]
# 3º argumento opcional: mínimo de minutos no lugar da mediana (teste de sensibilidade)
MINIMO = int(sys.argv[3]) if len(sys.argv) > 3 else None
if MINIMO:
    SUFIXO += f"_min{MINIMO}"
TOL = 1e-4
FRACAO, FRACAO_LEVE = 1.0, 0.5


def taxa(x, col):
    return x[col].fillna(0).to_numpy(float) / x.minutos.to_numpy(float) * 90


def outputs_dea(x, saidas):
    """Outputs em totais. Positivos como estão (deslocados se tiverem negativos); os "-" viram um índice."""
    mi = x.minutos.to_numpy(float)
    Y = {}
    for col, dirc in saidas:
        if dirc == "+":
            v = x[col].fillna(0).to_numpy(float)
            if (v < 0).any():
                t = taxa(x, col)
                v = (t - t.min()) * mi / 90
            Y[col] = v
    neg = [col for col, dirc in saidas if dirc == "-"]
    if neg:
        t = sum(taxa(x, col) for col in neg)
        Y["menos_erros"] = (t.max() - t) * mi / 90
    Y = pd.DataFrame(Y, index=x.index)
    return Y.loc[:, Y.sum() > 0]  # output zerado no grupo inteiro não informa nada


def criterios_topsis(x, saidas, extras):
    """Taxas por 90, todas convertidas em "quanto maior, melhor" (inputs entram como custo)."""
    M = []
    for col, dirc in saidas:
        if dirc == "+":
            t = taxa(x, col)
            M.append(t - t.min())
    neg = [col for col, dirc in saidas if dirc == "-"]
    if neg:
        t = sum(taxa(x, col) for col in neg)
        M.append(t.max() - t)
    if VARIANTE != "sem":
        v = x.valor_elenco_clube_eur.to_numpy(float)
        v = np.log10(v) if VARIANTE == "log" else v
        M.append(v.max() - v)
    for col in extras:
        t = taxa(x, col)
        M.append(t.max() - t)
    return np.column_stack(M)


def melhorar(y0, alvo, nomes):
    """Os dois outputs com maior folga relativa até a projeção na fronteira CCR."""
    folga = (alvo - y0) / np.maximum(y0, 1e-9)
    ordem = [i for i in np.argsort(-folga) if alvo[i] - y0[i] > 1e-6][:2]
    return "; ".join(f"{nomes[i]} (+{min(folga[i], 9.99):.0%})" for i in ordem)


b = pd.read_csv(f"{BASE}/base_analise_2026.csv")
a = b[(b.minutos >= MINIMO if MINIMO else b.acima_mediana) & b.grupo.notna()].copy()
saida, resumo = [], []
for g, x in a.groupby("grupo_lado"):
    x = x.reset_index(drop=True)
    x["xg_mais_xa"] = x.expected_goals.fillna(0) + x.expected_assists.fillna(0)
    extras = c.INPUTS_ATAQUE if g in c.GRUPOS_ATAQUE else []
    x["log_valor_clube"] = np.log10(x.valor_elenco_clube_eur)
    ins = {"valor": c.INPUTS, "log": ["minutos", "log_valor_clube"], "sem": ["minutos"]}[VARIANTE]
    X = x[ins + extras].fillna(0).to_numpy(float).copy()
    X[X <= 0] = 0.01  # input precisa ser positivo (xA zerado de algum jogador)
    Y = outputs_dea(x, c.OUTPUTS[g])
    e_ccr, lam = dea.ccr(X, Y.to_numpy())
    cats = ahp.grupos(x.grupo.iloc[0].removesuffix(" E").removesuffix(" D"), list(Y.columns))
    e_res, lam_res = dea.ccr_restrito(X, Y.to_numpy(), cats, FRACAO)
    e_leve, _ = dea.ccr_restrito(X, Y.to_numpy(), cats, FRACAO_LEVE)
    e_bcc, _ = dea.bcc(X, Y.to_numpy())
    sup = dea.supereficiencia(X, Y.to_numpy())
    cru = dea.eficiencia_cruzada(X, Y.to_numpy(), e_ccr)
    M = criterios_topsis(x, c.OUTPUTS[g], extras)
    top = dea.topsis(M, [True] * M.shape[1])
    # referências e pontos a melhorar saem do modelo principal (alvo orientado a output = lambda.Y / eficiência)
    alvo = (lam_res @ Y.to_numpy()) / e_res[:, None]
    r = x[["jogador_id", "nome", "time", "divisao_2026", "grupo", "grupo_lado", "minutos", "jogos", "idade",
           "valor_mercado_eur", "valor_elenco_clube_eur", "rating_medio", "goals", "assists",
           "expected_goals", "expected_assists"]].copy()
    r["restrito"], r["restrito_leve"] = e_res, e_leve
    r["ccr"], r["bcc"] = e_ccr, e_bcc
    r["escala"] = e_ccr / e_bcc
    r["supereficiencia"], r["cruzada"], r["topsis"] = sup, cru, top
    r["eficiente"] = e_res >= 1 - TOL  # modelo principal
    r["eficiente_leve"] = e_leve >= 1 - TOL
    r["eficiente_ccr"] = e_ccr >= 1 - TOL
    r["eficiente_bcc"] = e_bcc >= 1 - TOL
    r["referencias"] = ["; ".join(x.nome[j] for j in np.argsort(-lam_res[k])[:3] if lam_res[k, j] > 1e-6 and j != k)
                        for k in range(len(x))]
    r["melhorar_em"] = [melhorar(Y.to_numpy()[k], alvo[k], list(Y.columns)) for k in range(len(x))]
    for m in ["restrito", "supereficiencia", "cruzada", "topsis", "bcc", "ccr"]:
        r["rank_" + m] = r[m].rank(ascending=False, method="min").astype(int)
    saida.append(r)
    resumo.append({"grupo": g, "jogadores": len(x), "inputs": X.shape[1], "outputs": Y.shape[1],
                   "eficientes": int(r.eficiente.sum()), "pct": r.eficiente.mean(),
                   "eficientes_leve": int(r.eficiente_leve.sum()),
                   "eficientes_ccr": int(r.eficiente_ccr.sum()), "pct_ccr": r.eficiente_ccr.mean(),
                   "eficientes_bcc": int(r.eficiente_bcc.sum()), "pct_bcc": r.eficiente_bcc.mean(),
                   "super_inf": int(np.isinf(sup).sum())})
    print(f"{g}: {len(x)} jogadores, {X.shape[1]} inputs, {Y.shape[1]} outputs, "
          f"{r.eficiente.mean():.0%} eficientes (restrito), {r.eficiente_leve.mean():.0%} leve, "
          f"{r.eficiente_ccr.mean():.0%} CCR livre, {r.eficiente_bcc.mean():.0%} BCC", flush=True)

res = pd.concat(saida, ignore_index=True)
# análise só com xG/xA (sem DEA): saldo por 90 minutos
res["gols_menos_xg"] = res.goals.fillna(0) - res.expected_goals.fillna(0)
res["assist_menos_xa"] = res.assists.fillna(0) - res.expected_assists.fillna(0)
res["gols_menos_xg_p90"] = res.gols_menos_xg / res.minutos * 90
res["assist_menos_xa_p90"] = res.assist_menos_xa / res.minutos * 90
res.to_csv(f"{BASE}/resultados_dea_2026{SUFIXO}.csv", index=False)
pd.DataFrame(resumo).to_csv(f"{BASE}/resumo_dea_2026{SUFIXO}.csv", index=False)
t = pd.DataFrame(resumo)
print(f"\nTotal: {t.jogadores.sum()} jogadores | eficientes: restrito {t.eficientes.sum()} "
      f"({t.eficientes.sum() / t.jogadores.sum():.1%}), leve {t.eficientes_leve.sum()}, "
      f"CCR livre {t.eficientes_ccr.sum()}, BCC {t.eficientes_bcc.sum()}")

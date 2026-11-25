"""Modelos de eficiência usados no projeto (implementação própria com scipy/HiGHS).

X: matriz n x m de inputs (positivos). Y: matriz n x s de outputs (não negativos).
Todos os modelos são invariantes à unidade de medida; as colunas são escaladas pela média só para
estabilidade numérica.

- ccr / bcc          envelopamento orientado a output (Charnes et al., 1978; Banker et al., 1984).
                     Eficiência = 1/phi, em (0, 1]; 1 = na fronteira.
- ccr_restrito       CCR com restrição de peso virtual por categoria de outputs (Wong e Beasley, 1990),
                     com os pesos das categorias vindos do AHP (ver ahp.py).
- supereficiencia    Andersen e Petersen (1993), CCR orientado a input sem a própria DMU. > 1 para
                     eficientes; igual ao CCR para ineficientes. inf quando a DMU é a única com
                     algum output positivo (sem referência possível).
- eficiencia_cruzada Doyle e Green (1994), formulação benevolente: cada DMU escolhe, entre os pesos que
                     lhe dão a nota CCR máxima, os que mais favorecem as demais; a nota cruzada é a média
                     das notas que os pesos das outras DMUs dão a ela.
- topsis             Hwang e Yoon (1981), sem programação linear: distância ao ideal positivo e negativo.
"""
import numpy as np
from scipy.optimize import linprog

TOL = 1e-6


def _escala(M):
    M = np.asarray(M, dtype=float)
    media = M.mean(axis=0)
    media[media == 0] = 1.0
    return M / media


def _envelope(X, Y, k, vrs):
    """max phi  s.a.  sum(l x) <= x_k ;  phi y_k <= sum(l y) ;  [sum l = 1] ; l >= 0."""
    n, m = X.shape
    s = Y.shape[1]
    c = np.zeros(n + 1)
    c[0] = -1.0
    A = np.vstack([np.hstack([np.zeros((m, 1)), X.T]),
                   np.hstack([Y[k][:, None], -Y.T])])
    b = np.concatenate([X[k], np.zeros(s)])
    Aeq = np.hstack([[0.0], np.ones(n)])[None, :] if vrs else None
    beq = [1.0] if vrs else None
    r = linprog(c, A_ub=A, b_ub=b, A_eq=Aeq, b_eq=beq, bounds=[(0, None)] * (n + 1), method="highs")
    if r.status == 3:  # ilimitado: a DMU não tem output positivo
        return 0.0, np.zeros(n)
    if r.status != 0:
        raise RuntimeError(f"LP falhou para DMU {k}: {r.message}")
    phi = r.x[0]
    return 1.0 / phi, r.x[1:]


def ccr(X, Y, vrs=False):
    """Devolve (eficiências, matriz lambda n x n). Linha k = combinação de referência da DMU k."""
    X, Y = _escala(X), _escala(Y)
    n = X.shape[0]
    ef = np.zeros(n)
    lam = np.zeros((n, n))
    for k in range(n):
        ef[k], lam[k] = _envelope(X, Y, k, vrs)
    return np.minimum(ef, 1.0), lam


def bcc(X, Y):
    return ccr(X, Y, vrs=True)


def ccr_restrito(X, Y, grupos, fracao=1.0):
    """CCR multiplicadores com peso virtual mínimo por categoria de outputs.

    max u.y_k  s.a.  v.x_k = 1 ;  u.y_j - v.x_j <= 0 ;
    sum_{r em c} u_r.media(y_r) >= fracao . w_c . sum_i u_i.media(y_i)   para cada categoria c.

    grupos: lista de (índices das colunas de Y, peso w_c), com os pesos somando 1. Com fracao = 1 cada
    categoria responde exatamente por w_c (o modelo só escolhe como dividir dentro dela e os pesos dos
    inputs); com fracao = 0 é o CCR livre. Devolve (eficiências, lambdas = duais das restrições por DMU).
    """
    X, Y = _escala(X), _escala(Y)
    n, m = X.shape
    s = Y.shape[1]
    media = Y.mean(axis=0)
    R = np.zeros((len(grupos), s + m))
    for i, (idx, w) in enumerate(grupos):
        R[i, :s] = fracao * w * media
        R[i, idx] -= media[idx]
    A = np.vstack([np.hstack([Y, -X]), R])
    ef = np.zeros(n)
    lam = np.zeros((n, n))
    for k in range(n):
        c = np.concatenate([-Y[k], np.zeros(m)])
        r = linprog(c, A_ub=A, b_ub=np.zeros(len(A)),
                    A_eq=np.concatenate([np.zeros(s), X[k]])[None, :], b_eq=[1.0],
                    bounds=[(0, None)] * (s + m), method="highs")
        if r.status != 0:
            raise RuntimeError(f"LP restrito falhou para DMU {k}: {r.message}")
        ef[k] = -r.fun
        lam[k] = -r.ineqlin.marginals[:n]
    return np.minimum(ef, 1.0), lam


def supereficiencia(X, Y):
    X, Y = _escala(X), _escala(Y)
    n, m = X.shape
    s = Y.shape[1]
    out = np.zeros(n)
    for k in range(n):
        outros = [j for j in range(n) if j != k]
        Xo, Yo = X[outros], Y[outros]
        c = np.zeros(n)
        c[0] = 1.0  # min theta
        A = np.vstack([np.hstack([-X[k][:, None], Xo.T]),
                       np.hstack([np.zeros((s, 1)), -Yo.T])])
        b = np.concatenate([np.zeros(m), -Y[k]])
        r = linprog(c, A_ub=A, b_ub=b, bounds=[(0, None)] * n, method="highs")
        out[k] = r.x[0] if r.status == 0 else np.inf
    return out


def eficiencia_cruzada(X, Y, ef_ccr=None):
    X, Y = _escala(X), _escala(Y)
    n, m = X.shape
    s = Y.shape[1]
    if ef_ccr is None:
        ef_ccr, _ = ccr(X, Y)
    E = np.full((n, n), np.nan)  # E[d, j] = nota da DMU j com os pesos de d
    for d in range(n):
        outros = [j for j in range(n) if j != d]
        # variáveis: u (s), v (m). max u . sum(y_j, j != d)
        c = np.concatenate([-Y[outros].sum(axis=0), np.zeros(m)])
        A_ub = np.hstack([Y, -X])  # u y_j - v x_j <= 0
        b_ub = np.zeros(n)
        A_eq = np.vstack([np.concatenate([np.zeros(s), X[outros].sum(axis=0)]),          # v . sum(x_j) = 1
                          np.concatenate([Y[d], -ef_ccr[d] * X[d]])])                     # u y_d = theta* v x_d
        b_eq = [1.0, 0.0]
        r = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=[(0, None)] * (s + m), method="highs")
        if r.status != 0:  # cai para os pesos CCR simples
            c2 = np.concatenate([-Y[d], np.zeros(m)])
            r = linprog(c2, A_ub=A_ub, b_ub=b_ub, A_eq=np.concatenate([np.zeros(s), X[d]])[None, :], b_eq=[1.0],
                        bounds=[(0, None)] * (s + m), method="highs")
        u, v = r.x[:s], r.x[s:]
        E[d] = (Y @ u) / (X @ v)
    np.fill_diagonal(E, np.nan)
    return np.nanmean(E, axis=0)


def topsis(M, beneficio, pesos=None):
    """M: n x k critérios; beneficio: lista de bool (True = quanto maior melhor)."""
    M = np.asarray(M, dtype=float)
    norma = np.sqrt((M ** 2).sum(axis=0))
    norma[norma == 0] = 1.0
    R = M / norma
    w = np.ones(M.shape[1]) / M.shape[1] if pesos is None else np.asarray(pesos) / np.sum(pesos)
    V = R * w
    ben = np.asarray(beneficio)
    ideal = np.where(ben, V.max(axis=0), V.min(axis=0))
    anti = np.where(ben, V.min(axis=0), V.max(axis=0))
    dp = np.sqrt(((V - ideal) ** 2).sum(axis=1))
    dn = np.sqrt(((V - anti) ** 2).sum(axis=1))
    return dn / (dp + dn)

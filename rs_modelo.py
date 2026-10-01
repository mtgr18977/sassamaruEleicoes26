"""Governo do RS 2026: estimativa a partir das pesquisas, chances de ser eleito e distribuição regional (base 2022).

1º turno: três partes (Zucco/PL = D, Brizola/PDT = E, Souza/MDB = C) em logit-razão (referência Zucco); média ponderada
por amostra e recência, com a dispersão ENTRE pesquisas (efeitos de instituto + ruído) como incerteza. "Outros"
(Maranata e nanicos) saem como fatia fixa r̄. 2º turno: um logit por par (Z×B, Z×S, B×S) com piso de incerteza.
Os dois turnos são simulados juntos (correlação ASSUMIDA rho). Regional: swing em logit por unidade, calibrado aos totais.
"""
import json

import numpy as np
import pandas as pd

from pesquisas import SD_PISO_2T_PP
from rs_dados import blocos_por_unidade, carregar

CSV = "datasets/pesquisas-rs-governador-2026.csv"
SISTEMATICO_1T_PP = 3.6   # ASSUMIDO: erro sistemático das pesquisas (p.p. por candidato); proxy = RMSE medido nas pesquisas nacionais finais do 1º turno (sem histórico estadual)
HOJE = pd.Timestamp("2026-10-01")
TAU_DIAS, DEFF, RHO = 14.0, 1.5, 0.5
logit = lambda p: np.log(p / (1 - p))
inv = lambda y: 1 / (1 + np.exp(-y))


def preparar(csv=CSV):
    d = pd.read_csv(csv, parse_dates=["campo_ini", "campo_fim"])
    d["data"] = d.campo_fim
    cand = d.zucco + d.brizola + d.souza + d.maranata + d.outros
    d["z"], d["b"], d["s"] = d.zucco / cand, d.brizola / cand, d.souza / cand
    d["r"] = (d.maranata + d.outros) / cand
    tres = d.z + d.b + d.s
    d["z3"], d["b3"], d["s3"] = d.z / tres, d.b / tres, d.s / tres          # só os três principais
    return d


def _pesos(d, hoje):
    dias = (d.data - hoje).dt.days.to_numpy(float)
    return (d.amostra.to_numpy() / DEFF) * np.exp(dias / TAU_DIAS)


def estimar_1t(df, hoje=HOJE):
    d = df[df.data <= hoje]
    v = np.column_stack([np.log(d.b3 / d.z3), np.log(d.s3 / d.z3)])
    w = _pesos(d, hoje)
    mu = (w[:, None] * v).sum(0) / w.sum()
    dev = v - mu
    S = (w[:, None, None] * np.einsum("ni,nj->nij", dev, dev)).sum(0) / (w.sum() - (w ** 2).sum() / w.sum())   # entre pesquisas
    cov = (w ** 2).sum() / w.sum() ** 2 * S
    z, b, sx = np.exp([0, *mu]) / np.exp([0, *mu]).sum() * (1 - (w * d.r).sum() / w.sum())
    sg = (SISTEMATICO_1T_PP / 100) ** 2                          # erros independentes e iguais em cada parte -> delta no logit-razão
    cov = cov + sg * np.array([[1 / b ** 2 + 1 / z ** 2, 1 / z ** 2], [1 / z ** 2, 1 / sx ** 2 + 1 / z ** 2]])
    return dict(mu=mu, cov=cov, rbar=float((w * d.r).sum() / w.sum()), n=len(d))


def estimar_par(df, hoje, x, y, piso_pp=SD_PISO_2T_PP):
    """Logit do 2º turno do par (x vs y), média ponderada entre as pesquisas que trazem o par."""
    d = df[(df.data <= hoje)].dropna(subset=[x, y])
    t = np.log(d[x] / d[y]).to_numpy()
    w = _pesos(d, hoje)
    mu = (w * t).sum() / w.sum()
    S = (w * (t - mu) ** 2).sum() / (w.sum() - (w ** 2).sum() / w.sum())
    sd = np.sqrt((w ** 2).sum() / w.sum() ** 2 * S)
    p = inv(mu)
    return float(mu), float(max(sd, piso_pp / 100 / (p * (1 - p)))), len(d)


def parametros(df, hoje=HOJE):
    e = estimar_1t(df, hoje)
    pares = {k: estimar_par(df, hoje, *c) for k, c in {"ZB": ("r2_zb_z", "r2_zb_b"), "ZS": ("r2_zs_z", "r2_zs_s"), "BS": ("r2_bs_b", "r2_bs_s")}.items()}
    return dict(data=str(hoje.date()), mu=e["mu"].tolist(), cov=e["cov"].tolist(), rbar=e["rbar"], n=e["n"],
                pares={k: dict(mu=v[0], sd=v[1], n=v[2]) for k, v in pares.items()})


def chances(par, n=40000, rho=RHO, seed=1):
    rng = np.random.default_rng(seed)
    L = np.linalg.cholesky(np.array(par["cov"]))
    dev = rng.standard_normal((n, 2)) @ L.T
    v = np.array(par["mu"]) + dev
    e = np.exp(np.column_stack([np.zeros(n), v]))               # z, b, s (relativo a z)
    sh = e / e.sum(1, keepdims=True) * (1 - par["rbar"])
    c = par["cov"]
    sdp = {"ZB": np.sqrt(c[0][0]), "ZS": np.sqrt(c[1][1]), "BS": np.sqrt(c[0][0] + c[1][1] - 2 * c[0][1])}
    dp = {"ZB": -dev[:, 0], "ZS": -dev[:, 1], "BS": dev[:, 0] - dev[:, 1]}
    out1 = sh.max(1) > 0.5
    ordem = np.argsort(-sh, axis=1)
    top = np.sort(ordem[:, :2], axis=1)                          # (0,1)=ZB (0,2)=ZS (1,2)=BS
    par_nome = np.where((top[:, 0] == 0) & (top[:, 1] == 1), 0, np.where((top[:, 0] == 0), 1, 2))
    win = np.zeros((n, 3), bool)
    win[np.arange(n)[out1], ordem[out1, 0]] = True
    eps = rng.standard_normal(n)
    for k, (nome, (a, b)) in enumerate({"ZB": (0, 1), "ZS": (0, 2), "BS": (1, 2)}.items()):
        m = (~out1) & (par_nome == k)
        u = dp[nome] / sdp[nome]
        t = par["pares"][nome]["mu"] + par["pares"][nome]["sd"] * (rho * u + np.sqrt(1 - rho ** 2) * eps)
        win[m & (t > 0), a] = True
        win[m & (t <= 0), b] = True
    return dict(eleito=win.mean(0).round(4).tolist(), vence_1t=[float((out1 & (ordem[:, 0] == i)).mean()) for i in range(3)],
                segundo_turno=float((~out1).mean()), par_final={k: float(((~out1) & (par_nome == i)).mean()) for i, k in enumerate(["ZB", "ZS", "BS"])})


def ruido_unidade():
    """σ por eixo (logit) do ruído por unidade: média de duas medidas históricas dos resíduos do swing uniforme
    (ln(E/C) de 2002-2022, dividido por √2, e ln(D/E) de 2014-2022; D quase inexistia antes disso)."""
    u = blocos_por_unidade(carregar()); anos = sorted(u.ano.unique())
    def resid(num, den, pares):
        r = []
        for a_, b_ in pares:
            x, y = u[u.ano == a_].set_index("unidade_nome"), u[u.ano == b_].set_index("unidade_nome")
            d = np.log(y[num] / y[den]) - np.log(x[num] / x[den])
            r.append(d - np.average(d, weights=y.validos))
        return float(np.sqrt((pd.concat(r) ** 2).mean()))
    todos = list(zip(anos[:-1], anos[1:]))
    return (resid("E", "C", todos) / np.sqrt(2) + resid("D", "E", [(2014, 2018), (2018, 2022)])) / 2


def unidades():
    u = blocos_por_unidade(carregar()); u = u[u.ano == 2022].reset_index(drop=True)
    return u[["unidade_nome", "E", "C", "D", "validos"]]


def regioes(par, u, sigma, n=20000, rho=RHO, seed=2):
    """Simula o 1º turno por unidade (Z=D, B=E, S=C+outros) e o 2º turno Z×B por unidade."""
    rng = np.random.default_rng(seed)
    L = np.linalg.cholesky(np.array(par["cov"]))
    dev = rng.standard_normal((n, 2)) @ L.T
    e = np.exp(np.column_stack([np.zeros(n), np.array(par["mu"]) + dev]))
    sh = e / e.sum(1, keepdims=True) * (1 - par["rbar"])
    alvo = np.column_stack([sh[:, 0], sh[:, 1], sh[:, 2] + par["rbar"]])          # D, E, C
    w = (u.validos / u.validos.sum()).to_numpy()
    aE = np.log(u.E / u.D).to_numpy() + sigma * rng.standard_normal((n, len(u)))
    aC = np.log(u.C / u.D).to_numpy() + sigma * rng.standard_normal((n, len(u)))
    dE, dC = np.zeros(n), np.zeros(n)
    for _ in range(60):
        eE, eC = np.exp(aE + dE[:, None]), np.exp(aC + dC[:, None]); den = 1 + eE + eC
        D, E, C = 1 / den, eE / den, eC / den
        mD, mE, mC = D @ w, E @ w, C @ w
        dE += np.log(alvo[:, 1] / mE) - np.log(alvo[:, 0] / mD)
        dC += np.log(alvo[:, 2] / mC) - np.log(alvo[:, 0] / mD)
    c = par["cov"]; sd_zb = np.sqrt(c[0][0]); u_zb = -dev[:, 0] / sd_zb
    p = par["pares"]["ZB"]; t = p["mu"] + p["sd"] * (rho * u_zb + np.sqrt(1 - rho ** 2) * rng.standard_normal(n)); p2 = inv(t)
    q = D / (D + E); om = (D + E) * w; om = om / om.sum(1, keepdims=True)
    lo, hi = np.full(n, -3.0), np.full(n, 3.0)
    for _ in range(45):
        m = (lo + hi) / 2
        baixo = (om * inv(logit(q) + m[:, None])).sum(1) < p2
        lo, hi = np.where(baixo, m, lo), np.where(baixo, hi, m)
    q2 = inv(logit(q) + ((lo + hi) / 2)[:, None])
    pc = lambda x: np.percentile(x, [5, 50, 95], axis=0) * 100
    out = pd.DataFrame({"unidade": u.unidade_nome, "zucco": pc(D)[1], "brizola": pc(E)[1], "centro": pc(C)[1], "margem_zb": pc(D - E)[1], "margem_p5": pc(D - E)[0], "margem_p95": pc(D - E)[2],
                        "p_zucco_a_frente_1t": (D > E).mean(0) * 100, "zb2t": pc(q2)[1], "zb2t_p5": pc(q2)[0], "zb2t_p95": pc(q2)[2],
                        "p_zucco_vence_2t": (q2 > .5).mean(0) * 100})
    return out


if __name__ == "__main__":
    d = preparar()
    par = parametros(d)
    sh = np.exp([0, *par["mu"]]); sh = sh / sh.sum() * (1 - par["rbar"])
    print("parâmetros:", json.dumps({k: par[k] for k in ("mu", "rbar", "n")}), "\nshares (Z,B,S):", (100 * sh).round(1), "| outros", round(100 * par["rbar"], 1))
    print("sd marginais alr:", np.sqrt(np.diag(par["cov"])).round(3))
    for k, v in par["pares"].items():
        print(k, "2º turno: x/(x+y) =", round(100 * inv(v["mu"]), 1), "sd(logit)", round(v["sd"], 3), "n", v["n"])
    r = chances(par)
    print("chances:", r)
    sg = ruido_unidade(); print("σ por unidade:", round(sg, 3))
    pd.options.display.float_format = "{:.1f}".format
    reg = regioes(par, unidades(), sg)
    print(reg.round(1).to_string(index=False))
    u = unidades()
    json.dump(dict(par=par, sigma=sg, unidades=u.to_dict("records"), ref=dict(chances=r, regioes=reg.round(2).to_dict("records"))),
              open("modelos/rs-parametros.json", "w"), ensure_ascii=False, indent=1)

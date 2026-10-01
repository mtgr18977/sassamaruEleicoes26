"""Monte Carlo: swing uniforme + choque regional + ruído por UF/capital (ambos medidos no backtest).

Sorteio: p_nac ~ logit-normal(pesquisas, sd_logit); choque regional e ruído de unidade em logit;
um deslocamento comum é recalibrado para que a média ponderada (válidos 2022) = p_nac sorteado.
"""
import json
import numpy as np
import pandas as pd
from backtest import D, inv, logit
from nivel2 import REGIAO, transicoes

N = 20000
REGIAO["ZZ"] = "EX"  # exterior: região própria (~0,5% dos válidos), com o mesmo sd de choque
rng = np.random.default_rng(2026)


def ruido_historico(df, nac, turno):
    """(sd choque regional, sd ruído por unidade) em logit, dos resíduos do swing uniforme 2006–2022."""
    res = []
    for dy, d, _ in transicoes(df, nac, turno).values():
        res.append(pd.DataFrame({"r": dy - d, "g": [REGIAO[u] for u in dy.index]}))
    r = pd.concat(res, keys=range(len(res))).rename_axis(["t", "uf"]).reset_index()
    g = r.groupby(["t", "g"]).r
    var_uf = g.var(ddof=1).mean()
    var_med = g.mean().var(ddof=1) - (var_uf / g.size()).mean()
    return float(np.sqrt(max(var_med, 0))), float(np.sqrt(var_uf))


def gap_capitais(uf, cap, turno):
    """gap capital–estado (logit) por UF, sd do choque comum a todas as capitais e sd idiossincrático.
    Δgap entre eleições = deslocamento comum (média da transição) + resíduo por capital. DF (capital = UF) fica de fora."""
    m = cap[cap.turno == turno].merge(uf[uf.turno == turno], on=["ano", "uf"], suffixes=("_c", "_u"))
    m = m[m.uf != "DF"]
    m["gap"] = logit(m.pct_pt_validos_c / 100) - logit(m.pct_pt_validos_u / 100)
    g = m.pivot(index="uf", columns="ano", values="gap")
    d = g.diff(axis=1).iloc[:, 1:]
    return g[2022], float(np.sqrt((d.mean() ** 2).mean())), float((d - d.mean()).stack().std())


def simular(unid, p_nac, sd_nac, sd_reg, sd_uf):
    """unid: DataFrame(uf, pct_pt_validos, validos). Retorna (p_unidades[N,k], p_nac_sorteado[N])."""
    y0 = logit(unid.pct_pt_validos.to_numpy() / 100)
    w = unid.validos.to_numpy() / unid.validos.sum()
    regs = sorted(set(REGIAO[u] for u in unid.uf))
    idx = np.array([regs.index(REGIAO[u]) for u in unid.uf])
    alvo = inv(logit(p_nac) + sd_nac * rng.standard_normal(N))
    y = y0 + sd_reg * rng.standard_normal((N, len(regs)))[:, idx] + sd_uf * rng.standard_normal((N, len(y0)))
    lo, hi = np.full(N, -3.0), np.full(N, 3.0)
    for _ in range(50):
        m = (lo + hi) / 2
        baixo = (inv(y + m[:, None]) @ w) < alvo
        lo, hi = np.where(baixo, m, lo), np.where(baixo, hi, m)
    return inv(y + ((lo + hi) / 2)[:, None]), alvo


def main():
    par = json.load(open("modelos/parametros.json"))
    nac = pd.read_csv(D + "tse-presidente-nacional.csv").set_index(["ano", "turno"])
    uf = pd.read_csv(D + "tse-presidente-uf.csv")
    cap = pd.read_csv(D + "tse-presidente-capitais.csv")
    pd.options.display.float_format = "{:.1f}".format
    mc = {}
    for turno in (1, 2):
        pr = par[f"turno{turno}"]
        hist = uf[~uf.uf.isin(["ZZ", "VT"])]
        sd_reg, sd_uf = ruido_historico(hist, nac, turno)
        _, sd_cap = ruido_historico(cap, nac, turno)   # capital: choque regional já vem do estado
        print(f"\n######## {turno}º TURNO — Lula {pr['p_pesquisas']:.1%} | sd_logit nac {pr['sd_logit']:.3f} | "
              f"choque regional {sd_reg:.3f} | ruído UF {sd_uf:.3f} | ruído capital {sd_cap:.3f}")
        u = uf[(uf.ano == 2022) & (uf.turno == turno) & (uf.uf != "VT")].reset_index(drop=True)
        p, nacs = simular(u, pr["p_pesquisas"], pr["sd_logit"], sd_reg, sd_uf)
        print(f"P(Lula > 50% dos válidos nacional) = {(nacs > .5).mean():.1%}   "
              f"margem Lula–resto (p.p. dos válidos): mediana {100*(2*np.median(nacs)-1):+.1f}")
        if turno == 1:
            print(f"P(decisão no 2º turno) = {(nacs <= .5).mean():.1%}")
        q = np.percentile(p, [5, 50, 95], axis=0) * 100
        t = pd.DataFrame({"uf": u.uf, "2022": u.pct_pt_validos, "p5": q[0], "mediana": q[1], "p95": q[2],
                          "P(PT>50%)": (p > .5).mean(0) * 100}).sort_values("mediana", ascending=False)
        t.to_csv(f"modelos/previsao-uf-turno{turno}.csv", index=False)
        print(t.round(1).to_string(index=False))

        gap, sd_com, sd_id = gap_capitais(uf, cap, turno)
        print(f"\n-- Capitais {turno}º turno: estado simulado + gap 2022 + choque comum (sd {sd_com:.2f}) + ruído (sd {sd_id:.2f})")
        pos = {x: i for i, x in enumerate(u.uf)}
        comum = sd_com * rng.standard_normal((N, 1))
        c22 = cap[(cap.ano == 2022) & (cap.turno == turno)].set_index("uf")
        pc = {}
        for x in c22.index:
            if x == "DF":
                pc[x] = p[:, pos[x]]
            else:
                y = logit(p[:, pos[x]]) + gap[x] + comum[:, 0] + sd_id * rng.standard_normal(N)
                pc[x] = inv(y)
        pc = pd.DataFrame(pc)
        q = np.percentile(pc, [5, 50, 95], axis=0) * 100
        tc = pd.DataFrame({"uf": pc.columns, "capital": c22.loc[pc.columns, "municipio"].to_numpy(),
                           "2022": c22.loc[pc.columns, "pct_pt_validos"].to_numpy(), "p5": q[0], "mediana": q[1],
                           "p95": q[2], "P(PT>50%)": (pc > .5).mean().to_numpy() * 100}).sort_values("mediana", ascending=False)
        tc.to_csv(f"modelos/previsao-capitais-turno{turno}.csv", index=False)
        mc[f"turno{turno}"] = dict(
            sd_reg=round(sd_reg, 4), sd_uf=round(sd_uf, 4), sd_com=round(sd_com, 4), sd_id=round(sd_id, 4),
            unidades=[dict(uf=r.uf, regiao=REGIAO[r.uf], p2022=round(r.pct_pt_validos / 100, 6), validos=int(r.validos),
                           capital=str(c22.municipio.get(r.uf, "")), cap2022=round(float(c22.pct_pt_validos[r.uf]) / 100, 6) if r.uf in c22.index else None,
                           gap=None if r.uf == "DF" or r.uf not in gap.index else round(float(gap[r.uf]), 4))
                      for r in u.itertuples()])
        print(tc.round(1).to_string(index=False))
    par["mc"] = mc
    json.dump(par, open("modelos/parametros.json", "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()

"""Nível 2: y_i,t = y_i,t0 + λ_g·δ, com λ por região (ridge em torno de 1).

λ estimado só com transições já ocorridas (janela expansiva, sem olhar o futuro)
e, para comparação otimista, em leave-one-out. δ é o real (oráculo), como no swing uniforme.
"""
import numpy as np
import pandas as pd
from backtest import D, inv, logit, swing_uniforme

REGIAO = {**dict.fromkeys("AC AM AP PA RO RR TO".split(), "N"),
          **dict.fromkeys("AL BA CE MA PB PE PI RN SE".split(), "NE"),
          **dict.fromkeys("DF GO MS MT".split(), "CO"),
          **dict.fromkeys("ES MG RJ SP".split(), "SE"),
          **dict.fromkeys("PR RS SC".split(), "S")}
KAPPA = 1.0  # força do prior λ=1 (fixado a priori, não ajustado no backtest)


def transicoes(df, nac, turno):
    """{(t0, t): (Δy por UF, δ nacional, regiões)}"""
    anos = sorted(df.ano.unique())
    out = {}
    for t0, t in zip(anos[:-1], anos[1:]):
        a = df[(df.ano == t) & (df.turno == turno)].set_index("uf")
        b = df[(df.ano == t0) & (df.turno == turno)].set_index("uf")
        idx = a.index.intersection(b.index)
        a, b = a.loc[idx], b.loc[idx]
        pa, pb = (a.pct_pt_validos / 100).clip(1e-4, 1 - 1e-4), (b.pct_pt_validos / 100).clip(1e-4, 1 - 1e-4)
        _, d = swing_uniforme(pb, nac.loc[(t, turno), "pct_pt_validos"] / 100, a.validos)
        out[(t0, t)] = (logit(pa) - logit(pb), d, a.validos)
    return out


def estimar_lambda(trans):
    sxy, sxx = {}, {}
    for dy, d, _ in trans:
        for uf, v in dy.items():
            g = REGIAO[uf]
            sxy[g] = sxy.get(g, 0) + v * d
            sxx[g] = sxx.get(g, 0) + d * d
    return {g: (sxy[g] + KAPPA) / (sxx[g] + KAPPA) for g in sxy}


def rodar(df, nac, turno, modo):
    tr = transicoes(df, nac, turno)
    linhas, lams = [], {}
    for (t0, t), (dy, d, w) in tr.items():
        if modo == "passado":
            treino = [v for (a, b), v in tr.items() if b < t]
        else:
            treino = [v for k, v in tr.items() if k != (t0, t)]
        if not treino:
            continue
        lam = estimar_lambda(treino)
        lams[t] = lam
        a = df[(df.ano == t) & (df.turno == turno)].set_index("uf").loc[dy.index]
        b = df[(df.ano == t0) & (df.turno == turno)].set_index("uf").loc[dy.index]
        prev = (b.pct_pt_validos / 100).clip(1e-4, 1 - 1e-4)
        real = a.pct_pt_validos / 100
        l = pd.Series([lam.get(REGIAO[u], 1.0) for u in dy.index], index=dy.index)
        pred = inv(logit(prev) + l * d)
        # recalibra δ para o total nacional bater (λ muda a média ponderada)
        lo, hi = -3.0, 3.0
        alvo = nac.loc[(t, turno), "pct_pt_validos"] / 100
        for _ in range(60):
            m = (lo + hi) / 2
            if (inv(logit(prev) + l * m) * w).sum() / w.sum() < alvo:
                lo = m
            else:
                hi = m
        pred = inv(logit(prev) + l * m)
        e = (pred - real) * 100
        linhas.append(dict(ano=t, turno=turno, MAE_pp=e.abs().mean()))
    return pd.DataFrame(linhas), lams


if __name__ == "__main__":
    from backtest import backtest
    nac = pd.read_csv(D + "tse-presidente-nacional.csv").set_index(["ano", "turno"])
    uf = pd.read_csv(D + "tse-presidente-uf.csv")
    uf = uf[~uf.uf.isin(["ZZ", "VT"])]
    base, _ = backtest(uf, "uf")
    base = base.pivot_table(index=["turno", "ano"], columns="modelo", values="MAE_pp")
    res = {}
    for modo in ("passado", "leave-one-out"):
        for turno in (1, 2):
            r, lams = rodar(uf, nac, turno, modo)
            res[(modo, turno)] = r.set_index(["turno", "ano"]).MAE_pp
            if modo == "passado" and turno == 1:
                print("λ por região (1º turno, janela passada):")
                print(pd.DataFrame(lams).T.round(2).to_string())
    t = base.join(pd.DataFrame({f"nível2 {m}": pd.concat([res[(m, 1)], res[(m, 2)]]) for m in ("passado", "leave-one-out")}))
    pd.options.display.float_format = "{:.2f}".format
    print("\nMAE por UF (p.p.), δ real:\n", t.to_string())
    print("\nMédia por turno:\n", t.groupby("turno").mean().to_string())

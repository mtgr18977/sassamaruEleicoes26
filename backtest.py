"""Baselines (persistência, swing uniforme) + backtest leave-one-election-out.

Prevê % PT nos válidos por UF/capital em t a partir de t-1 (mesmo turno).
Swing uniforme usa o δ REAL (oráculo): mede só o erro da distribuição entre unidades.
"""
import numpy as np
import pandas as pd

D = "datasets/"
logit = lambda p: np.log(p / (1 - p))
inv = lambda y: 1 / (1 + np.exp(-y))


def swing_uniforme(prev, p_real_nac, w):
    """Acha δ tal que a média ponderada (pesos w = válidos reais) bate com o % nacional real."""
    y = logit(prev)
    lo, hi = -3.0, 3.0
    for _ in range(60):
        d = (lo + hi) / 2
        if (inv(y + d) * w).sum() / w.sum() < p_real_nac:
            lo = d
        else:
            hi = d
    return inv(y + d), d


def backtest(df, chave):
    nac = pd.read_csv(D + "tse-presidente-nacional.csv").set_index(["ano", "turno"])
    anos = sorted(df.ano.unique())
    linhas, det = [], []
    for turno in (1, 2):
        for t, t0 in zip(anos[1:], anos[:-1]):
            a = df[(df.ano == t) & (df.turno == turno)].set_index(chave)
            b = df[(df.ano == t0) & (df.turno == turno)].set_index(chave)
            idx = a.index.intersection(b.index)
            a, b = a.loc[idx], b.loc[idx]
            real, prev = a.pct_pt_validos / 100, b.pct_pt_validos / 100
            if turno == 2 and (a.pct_outros_validos > 0).any():
                continue
            pnac = nac.loc[(t, turno), "pct_pt_validos"] / 100
            sw, d = swing_uniforme(prev.clip(1e-4, 1 - 1e-4), pnac, a.validos)
            for nome, pred in (("persistência", prev), ("swing uniforme (δ real)", sw)):
                e = (pred - real) * 100
                linhas.append(dict(ano=t, turno=turno, modelo=nome, MAE_pp=e.abs().mean(),
                                   venc_certo=((pred > .5) == (real > .5)).mean(), delta=d))
                det.append(pd.DataFrame(dict(ano=t, turno=turno, modelo=nome, erro_pp=e)).reset_index())
    return pd.DataFrame(linhas), pd.concat(det)


if __name__ == "__main__":
    uf = pd.read_csv(D + "tse-presidente-uf.csv")
    uf = uf[~uf.uf.isin(["ZZ", "VT"])]
    cap = pd.read_csv(D + "tse-presidente-capitais.csv")
    pd.options.display.float_format = "{:.2f}".format
    for nome, df, ch in (("UF", uf, "uf"), ("Capitais", cap, "uf")):
        r, _ = backtest(df, ch)
        print(f"\n=== {nome}: erro absoluto médio (p.p.) e acerto do vencedor ===")
        print(r.pivot_table(index=["turno", "ano"], columns="modelo", values=["MAE_pp", "venc_certo"]).to_string())
        print(r.groupby(["turno", "modelo"])[["MAE_pp", "venc_certo"]].mean().to_string())

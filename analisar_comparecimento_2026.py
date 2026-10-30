"""Teste do comparecimento por município e UF: a virada de Lula acompanha o aumento do comparecimento entre os turnos?

  python analisar_comparecimento_2026.py
Entradas: datasets/tse_raw/detalhe_votacao_munzona_2026.zip (dados abertos do TSE, regerado em 30/10/2026; eleitorado e comparecimento por zona, 1º e 2º turnos, arquivo _BR) e
datasets/tse-presidente-municipio.csv (votos por município, de fetch_tse.py). Sem o exterior. Saída: modelos/comparecimento-2026.json.
Comparecimento = comparecidos / aptos. "Desloc." = Lula/(Lula+Flávio) no 2º turno − no 1º, em p.p. Correlações e médias são ponderadas pelo eleitorado quando dito."""
import json
import zipfile

import numpy as np
import pandas as pd

r1, r2 = (lambda x: round(float(x), 1)), (lambda x: round(float(x), 2))
REG = {**dict.fromkeys(["RR", "AP", "AC", "AM", "PA", "RO", "TO"], "Norte"), **dict.fromkeys(["MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA"], "Nordeste"),
       **dict.fromkeys(["MT", "MS", "GO", "DF"], "Centro-Oeste"), **dict.fromkeys(["SP", "RJ", "MG", "ES"], "Sudeste"), **dict.fromkeys(["PR", "SC", "RS"], "Sul")}


def carregar() -> pd.DataFrame:
    with zipfile.ZipFile("datasets/tse_raw/detalhe_votacao_munzona_2026.zip") as z:
        d = pd.read_csv(z.open("detalhe_votacao_munzona_2026_BR.csv"), sep=";", encoding="latin-1", dtype=str)
    d = d[(d.DS_CARGO == "Presidente") & (d.SG_UF != "ZZ")].copy()
    for c in ("QT_APTOS", "QT_COMPARECIMENTO"):
        d[c] = d[c].astype(int)
    d["cod5"] = d.CD_MUNICIPIO.str.zfill(5)
    g = d.pivot_table(index=["SG_UF", "cod5", "NM_MUNICIPIO"], columns="NR_TURNO", values=["QT_APTOS", "QT_COMPARECIMENTO"], aggfunc="sum").reset_index()
    g.columns = ["uf", "cod5", "municipio", "ap1", "ap2", "c1", "c2"]
    v = pd.read_csv("datasets/tse-presidente-municipio.csv", dtype={"cod_municipio": str})
    v = v[v.ano == 2026].assign(cod5=lambda x: x.cod_municipio.str.zfill(5))
    a, b = v[v.turno == 1].set_index("cod5"), v[v.turno == 2].set_index("cod5")
    g = g.set_index("cod5")
    g["L1"], g["F1"], g["L2"], g["F2"] = a.votos_pt, a.votos_antipt, b.votos_pt, b.votos_antipt
    g = g.dropna().reset_index()
    g["t1"], g["t2"] = 100 * g.c1 / g.ap1, 100 * g.c2 / g.ap2
    g["dt"] = g.t2 - g.t1
    g["l1"], g["l2"] = 100 * g.L1 / (g.L1 + g.F1), 100 * g.L2 / (g.L2 + g.F2)
    g["dl"] = g.l2 - g.l1
    return g


def corr_pond(x, y, w) -> float:
    c = np.cov(x, y, aweights=w)
    return float(c[0, 1] / np.sqrt(c[0, 0] * c[1, 1]))


def main() -> None:
    g = carregar()
    w = g.ap1.values
    ap, c1, c2 = int(g.ap1.sum()), int(g.c1.sum()), int(g.c2.sum())
    L1, F1, L2, F2 = (int(g[k].sum()) for k in ("L1", "F1", "L2", "F2"))
    extra = c2 - c1
    brasil = dict(aptos=ap, comp1=c1, comp2=c2, t1=r1(100 * c1 / ap), t2=r1(100 * c2 / g.ap2.sum()), extra=extra, dl_votos=L2 - L1, df_votos=F2 - F1,
                  # limite superior: se TODO o aumento de comparecimento tivesse ido para Lula, quanto ele teria (Lula/(Lula+Flávio)) com o comparecimento do 1º turno?
                  l1=r1(100 * L1 / (L1 + F1)), l2=r1(100 * L2 / (L2 + F2)), l2_sem_extra_tudo_lula=r1(100 * (L2 - extra) / (L2 - extra + F2)),
                  parte_do_ganho_de_lula_no_limite=r1(100 * extra / (L2 - L1)))
    # ---- município
    X = np.column_stack([np.ones(len(g)), g.dt]); W = np.sqrt(w)
    beta = np.linalg.lstsq(X * W[:, None], g.dl.values * W, rcond=None)[0]
    quint = []
    for q, x in g.groupby(pd.qcut(g.dt, 5, duplicates="drop"), observed=True):
        quint.append(dict(n=int(len(x)), dt=r1(np.average(x.dt, weights=x.ap1)), dl=r1(np.average(x.dl, weights=x.ap1)), t1=r1(np.average(x.t1, weights=x.ap1)), l1=r1(np.average(x.l1, weights=x.ap1))))
    quart_l = []
    for q, x in g.groupby(pd.qcut(g.l1, 4, labels=["25% menos Lula", "2º quartil", "3º quartil", "25% mais Lula"]), observed=True):
        quart_l.append(dict(grupo=str(q), n=int(len(x)), l1=r1(np.average(x.l1, weights=x.ap1)), dt=r1(np.average(x.dt, weights=x.ap1)), dl=r1(np.average(x.dl, weights=x.ap1))))
    porte = []
    for q, x in g.groupby(pd.cut(g.ap1, [0, 10000, 50000, 200000, 1e9], labels=["até 10 mil eleitores", "10 a 50 mil", "50 a 200 mil", "mais de 200 mil"]), observed=True):
        porte.append(dict(porte=str(q), n=int(len(x)), t1=r1(100 * x.c1.sum() / x.ap1.sum()), t2=r1(100 * x.c2.sum() / x.ap2.sum()), dl=r1(np.average(x.dl, weights=x.ap1))))
    municipio = dict(n=int(len(g)), dt_mediano=r1(g.dt.median()), dt_ponderado=r1(100 * c2 / g.ap2.sum() - 100 * c1 / ap), subiu=int((g.dt > 0).sum()), caiu=int((g.dt < 0).sum()),
                     corr=r2(np.corrcoef(g.dt, g.dl)[0, 1]), corr_pond=r2(corr_pond(g.dt, g.dl, w)), corr_l1_dt=r2(corr_pond(g.l1, g.dt, w)), corr_l1_dl=r2(corr_pond(g.l1, g.dl, w)),
                     inclinacao=r2(beta[1]), constante=r2(beta[0]), quintis=quint, quartis_lula=quart_l, porte=porte)
    # ---- UF
    u = g.groupby("uf").apply(lambda x: pd.Series(dict(ap=x.ap1.sum(), t1=100 * x.c1.sum() / x.ap1.sum(), t2=100 * x.c2.sum() / x.ap2.sum(), l1=100 * x.L1.sum() / (x.L1.sum() + x.F1.sum()),
                                                     l2=100 * x.L2.sum() / (x.L2.sum() + x.F2.sum()), dc=int(x.c2.sum() - x.c1.sum()), dL=int(x.L2.sum() - x.L1.sum()), dF=int(x.F2.sum() - x.F1.sum()))), include_groups=False)
    u["dt"], u["dl"] = u.t2 - u.t1, u.l2 - u.l1
    ufs = [dict(uf=i, regiao=REG[i], t1=r1(r.t1), t2=r1(r.t2), dt=r1(r["dt"]), dl=r1(r["dl"]), dc=int(r.dc), dL=int(r.dL), dF=int(r.dF)) for i, r in u.sort_values("dt").iterrows()]
    uf_corr = dict(corr=r2(np.corrcoef(u.dt, u.dl)[0, 1]), corr_pond=r2(corr_pond(u.dt, u.dl, u.ap.values)), n=int(len(u)))
    # ---- extremos e dispersão
    grandes = g[g.ap1 >= 50000]
    lin = lambda r: dict(uf=r.uf, municipio=r.municipio.title(), aptos=int(r.ap1), t1=r1(r.t1), t2=r1(r.t2), dt=r1(r["dt"]), dl=r1(r["dl"]))
    extremos = dict(mais_subiu=[lin(r) for _, r in grandes.sort_values("dt", ascending=False).head(8).iterrows()], mais_caiu=[lin(r) for _, r in grandes.sort_values("dt").head(8).iterrows()])
    pts = g[g.ap1 >= 20000]
    disp = [[r1(a), r1(b), int(c), u_] for a, b, c, u_ in zip(pts.dt, pts.dl, pts.ap1, pts.uf)]
    json.dump(dict(brasil=brasil, municipio=municipio, ufs=ufs, uf_corr=uf_corr, extremos=extremos, dispersao=disp), open("modelos/comparecimento-2026.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(brasil); print({k: v for k, v in municipio.items() if k not in ("quintis", "quartis_lula", "porte")}); print(uf_corr)
    for q in quint: print(q)
    for q in quart_l: print(q)


if __name__ == "__main__":
    main()

"""Agregador de pesquisas: tendência suavizada por candidato, com intervalo de 90%, para os gráficos das duas abas.

Cada candidato é a fatia dos votos válidos citados na pesquisa (x / soma dos candidatos; brancos, nulos e indecisos saem).
Por dia: média em logit, ponderada por amostra efetiva × núcleo gaussiano no tempo (largura SIGMA_DIAS), depois de tirar o
house effect do instituto (desvio médio do instituto contra a própria tendência, encolhido para 0 com poucas pesquisas).
Intervalo: erro amostral ponderado + incerteza dos house effects + piso de PISO_PP p.p. (erro sistemático assumido).
ponytail: não é um filtro de Kalman; é uma regressão local. Fora do intervalo das pesquisas o intervalo não é estendido.
"""
import numpy as np
import pandas as pd

DEFF = 1.5          # efeito de desenho: amostra efetiva = n / DEFF
Z90 = 1.645
SHRINK = 2.0        # pseudo-pesquisas que puxam o house effect para 0
PISO_PP = 1.0       # ASSUMIDO: piso do erro sistemático (p.p.) mesmo com muitas pesquisas
logit = lambda p: np.log(p / (1 - p))
inv = lambda y: 1 / (1 + np.exp(-y))


def tendencia(d, series, hoje, sigma=7.0, passo=1):
    """d: DataFrame com colunas data, instituto, n e uma coluna de fatia (0–1) por série.
    series: {nome: coluna}. Retorna {nome: [{data, m, lo, hi}]} (em %) de uma pesquisa até `hoje`, e os pontos."""
    d = d.dropna(subset=list(series.values())).sort_values("data").reset_index(drop=True)
    t = (d.data - hoje).dt.days.to_numpy(float)
    grade = np.arange(t.min(), 0 + 1, passo)
    insts = sorted(d.instituto.unique())
    out, pts = {}, {}
    for nome, col in series.items():
        p = d[col].clip(0.005, 0.995).to_numpy()
        y = logit(p)
        var = 1 / (d.n.to_numpy() / DEFF * p * (1 - p))
        h = {i: 0.0 for i in insts}
        for _ in range(3):                                   # house effect <-> tendência, 3 iterações
            ya = y - d.instituto.map(h).to_numpy()
            m_pt = np.array([_suave(t, ya, var, ti, sigma)[0] for ti in t])
            res = y - m_pt
            for i in insts:
                r = res[(d.instituto == i).to_numpy()]
                h[i] = r.sum() / (len(r) + SHRINK)
            mh = np.mean(list(h.values()))
            h = {i: v - mh for i, v in h.items()}            # soma zero: o nível é a média dos institutos
        var_h = np.var(list(h.values()), ddof=1) / len(insts) if len(insts) > 1 else 0.0
        ya = y - d.instituto.map(h).to_numpy()
        serie = []
        for ti in grade:
            m, v = _suave(t, ya, var, ti, sigma)
            sd = np.sqrt(v + var_h + (PISO_PP / 100 / (inv(m) * (1 - inv(m)))) ** 2)
            serie.append(dict(data=str((hoje + pd.Timedelta(days=int(ti))).date()), m=round(100 * float(inv(m)), 2),
                              lo=round(100 * float(inv(m - Z90 * sd)), 2), hi=round(100 * float(inv(m + Z90 * sd)), 2)))
        out[nome] = serie
        pts[nome] = [dict(data=str(r.data.date()), inst=r.instituto, v=round(100 * float(inv(y[k])), 2)) for k, r in enumerate(d.itertuples())]
    return out, pts, {i: {nome: None for nome in series} for i in insts}


def _suave(t, y, var, t0, sigma):
    k = np.exp(-0.5 * ((t - t0) / sigma) ** 2)
    w = k / var
    m = (w * y).sum() / w.sum()
    v = (w * w * var).sum() / w.sum() ** 2
    return m, v


def presidente(hoje, csv="datasets/pesquisas-2026.csv"):
    from pesquisas import preparar
    d = preparar(csv)
    c = ["t1_lula", "t1_flavio", "t1_caiado", "t1_zema", "t1_renan", "t1_cury", "t1_outros"]
    d = d[d[c].notna().all(axis=1)].copy()
    tot = d[c].sum(axis=1)
    d["lula"], d["flavio"] = d.t1_lula / tot, d.t1_flavio / tot
    d["demais"] = 1 - d.lula - d.flavio
    for k in ("caiado", "zema", "renan"):
        d[k] = d[f"t1_{k}"] / tot
    series = {"Lula (PT)": "lula", "Flávio Bolsonaro (PL)": "flavio", "Demais candidatos": "demais"}
    s, p, _ = tendencia(d, series, hoje)
    return dict(series=s, pontos=p)


def rs(hoje, csv="datasets/pesquisas-rs-governador-2026.csv"):
    import rs_modelo as rm
    d = rm.preparar(csv)
    d["n"] = d.amostra
    d["demais"] = d.r                                     # Maranata + outros, % dos candidatos citados
    series = {"Luciano Zucco (PL)": "z", "Juliana Brizola (PDT)": "b", "Gabriel Souza (MDB)": "s", "Demais": "demais"}
    s, p, _ = tendencia(d, series, hoje, sigma=10.0)
    return dict(series=s, pontos=p)


if __name__ == "__main__":
    h = pd.Timestamp("2026-10-02")
    for nome, f in (("Presidente", presidente), ("RS", rs)):
        r = f(h)
        print(nome)
        for k, v in r["series"].items():
            u = v[-1]
            print(f"  {k:24s} {u['m']:5.1f}% ({u['lo']:.1f}–{u['hi']:.1f}), {len(v)} dias")

"""Modelo do Senado: a vaga é da Direita? em função do voto presidencial da UF (mesmo dia de eleição).

P(vaga da Direita na UF) = σ(α + β · logit(x)), com x = Lula-contra-Flávio invertido: x = anti-PT / (anti-PT + PT) no 1º turno presidencial da UF.
Cada eleição tem o seu (α, β), ajustado por máxima verossimilhança (binomial: n vagas na UF, D da Direita). Dois parâmetros, 27 UFs por eleição,
então é um modelo pequeno: o ajuste é instável e eu mostro isso em vez de esconder.

Dois resultados que o modelo sustenta (ver `backtest`):
 * β (o quanto a presidencial explica o Senado) sobe de eleição em eleição: o voto no Senado se nacionalizou;
 * α (o "nível" nacional da Direita no Senado) NÃO é previsível pelos parâmetros da eleição anterior: o modelo erra o total, não a distribuição.
Por isso o produto é condicional: dado o total nacional de cadeiras da Direita, quais UFs. Em 2026 o x vem da projeção presidencial do site
(modelos/previsao-uf-turno1.csv: mediana de Lula/(Lula+Flávio) por UF), porque a presidencial por UF de 2026 ainda não saiu do TSE."""
import numpy as np
import pandas as pd

import senado

D = "datasets/"
ANOS = [2014, 2018, 2022, 2026]
lg = lambda x: np.log(x / (1 - x))
sg = lambda z: 1 / (1 + np.exp(-z))


def painel():
    """UF × eleição: n vagas, D eleitos da Direita, x (parcela anti-PT entre PT e anti-PT no 1º turno presidencial da UF)."""
    pres = pd.read_csv(D + "tse-presidente-uf.csv").query("turno == 1")
    pres = pres.assign(x=pres.pct_antipt_validos / (pres.pct_antipt_validos + pres.pct_pt_validos))
    proj = pd.read_csv("modelos/previsao-uf-turno1.csv").set_index("uf")
    out = {}
    for y in ANOS:
        d = pd.read_csv(D + f"tse-senado-{y}.csv")
        d["bloco"] = d.partido.map(senado.lin).map(senado.bloco)
        e = d[d.situacao == "ELEITO"].groupby("uf").agg(n=("bloco", "size"), D=("bloco", lambda s: int((s == "D").sum())))
        e["x"] = (1 - proj.mediana / 100).reindex(e.index) if y == 2026 else pres[pres.ano == y].set_index("uf").x.reindex(e.index)
        assert e.x.notna().all(), y
        out[y] = e
    return out


def ajustar(e):
    """(α, β) por IRLS (binomial, logit) com um ridge mínimo para não divergir com poucos pontos."""
    X = np.column_stack([np.ones(len(e)), lg(e.x.values)])
    y, n, b = e.D.values.astype(float), e.n.values.astype(float), np.zeros(2)
    for _ in range(80):
        p = sg(X @ b)
        W = n * p * (1 - p) + 1e-9
        z = X @ b + (y - n * p) / W
        b = np.linalg.solve(X.T @ (W[:, None] * X) + 1e-6 * np.eye(2), X.T @ (W * z))
    return float(b[0]), float(b[1])


def probabilidade(a, b, x):
    return sg(a + b * lg(np.asarray(x, dtype=float)))


def alfa_para_total(e, beta, total):
    """α que faz o modelo esperar `total` cadeiras da Direita (bisseção): a parte 'nível nacional' dada, só a distribuição por UF fica no modelo."""
    f = lambda a: float((e.n * probabilidade(a, beta, e.x)).sum()) - total
    lo, hi = -15.0, 15.0
    for _ in range(80):
        m = (lo + hi) / 2
        lo, hi = (lo, m) if f(lo) * f(m) <= 0 else (m, hi)
    return (lo + hi) / 2


def trocadas(esperado, real):
    return float(np.abs(np.asarray(esperado) - np.asarray(real)).sum() / 2)


def ranking(e, total):
    """Régua: dá as vagas da Direita às UFs de maior x até somar `total` (o mesmo total real: só mede a ordem das UFs)."""
    pr, resto = pd.Series(0, index=e.index), int(total)
    for uf in e.sort_values("x", ascending=False).index:
        pr[uf] = min(int(e.n[uf]), resto)
        resto -= pr[uf]
    return pr


def construir():
    P = painel()
    aj = {y: ajustar(P[y]) for y in ANOS}
    ajustes = [dict(ano=y, alfa=round(aj[y][0], 2), beta=round(aj[y][1], 2), vagas=int(P[y].n.sum()), direita=int(P[y].D.sum()),
                    corr=round(float(np.corrcoef(P[y].x, P[y].D / P[y].n)[0, 1]), 2), x_medio=round(float(P[y].x.mean()), 3)) for y in ANOS]
    back = []
    for y, ant in ((2018, 2014), (2022, 2018), (2026, 2022)):
        e, (a0, b0) = P[y], aj[ant]
        p = probabilidade(a0, b0, e.x)
        a1 = alfa_para_total(e, b0, e.D.sum())
        p1 = probabilidade(a1, b0, e.x)
        back.append(dict(ano=y, ref=ant, real=int(e.D.sum()), vagas=int(e.n.sum()), esperado=round(float((p * e.n).sum()), 1), trocadas=round(trocadas(p * e.n, e.D), 1),
                         alfa_cal=round(a1, 2), trocadas_cal=round(trocadas(p1 * e.n, e.D), 1), trocadas_rank=round(trocadas(ranking(e, e.D.sum()), e.D), 1)))
    # 2026 UF a UF: parâmetros de 2022 com o α calibrado ao total real (a distribuição que o modelo daria sabendo o total)
    e = P[2026]
    pc = probabilidade(back[-1]["alfa_cal"], aj[2022][1], e.x)
    ufs = [dict(uf=uf, x=round(float(r.x), 3), n=int(r.n), D=int(r.D), pD=round(float(pc[i]), 3), esperado=round(float(pc[i] * r.n), 2)) for i, (uf, r) in enumerate(e.iterrows())]
    for u in ufs:
        u["res"] = round(u["D"] - u["esperado"], 2)
    # curvas (por vaga) para o gráfico: x de 0,25 a 0,80
    xs = np.linspace(0.25, 0.80, 23)
    curvas = {str(y): [round(float(v), 3) for v in probabilidade(*aj[y], xs)] for y in (2018, 2022, 2026)}
    curvas["2026_cal"] = [round(float(v), 3) for v in probabilidade(back[-1]["alfa_cal"], aj[2022][1], xs)]
    return dict(ajustes=ajustes, backtest=back, ufs=ufs, xs=[round(float(v), 3) for v in xs], curvas=curvas)


if __name__ == "__main__":
    r = construir()
    print(pd.DataFrame(r["ajustes"]).to_string(index=False))
    print(pd.DataFrame(r["backtest"]).to_string(index=False))

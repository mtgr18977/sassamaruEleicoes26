"""Camada de pesquisas: estima δ (swing nacional em logit vs. 2022) com house effect e incerteza.

Por turno: logit(p) = nível + tendência linear + efeito do instituto (soma zero), WLS com peso
amostral × decaimento por recência. Nível = média dos 4 institutos hoje (viés absoluto não é
identificável; vai na incerteza via SD_VIES_HIST).
p(1º turno) = Lula / válidos;  p(2º turno) = Lula / (Lula + Flávio).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HOJE = pd.Timestamp("2026-10-01")
TAU_DIAS = 14.0        # meia-vida do decaimento ≈ TAU·ln2
DEFF = 1.5             # efeito de desenho: amostra efetiva = n / DEFF
SD_VIES_HIST = 0.02    # padrão de estimar(); main() usa o RMSE medido por turno (vies_rmse)
HORIZONTE = {1: 3, 2: 24}   # dias de 1/10 até 4/10 e 25/10: a incerteza da tendência cresce com o prazo
P2022 = {1: 0.484307, 2: 0.509024}  # % PT nos válidos, tse-presidente-nacional.csv
logit = lambda p: np.log(p / (1 - p))


def vies_rmse(turno, csv="datasets/vies-pesquisas.csv", nac="datasets/tse-presidente-nacional.csv"):
    """RMSE (em p, não p.p.) da parcela Lula/(Lula+rival) das pesquisas finais 2018/2022 vs. resultado.
    Inclui o viés médio (as pesquisas erraram para o lado do PT). ponytail: poucos pontos (4–5 por turno,
    2 eleições, 3 institutos); RTBD 2022 não localizado. Vale como ordem de grandeza."""
    v = pd.read_csv(csv).query("turno == @turno")
    n = pd.read_csv(nac).set_index(["ano", "turno"])
    real = [n.loc[(a, turno), "votos_pt"] / (n.loc[(a, turno), "votos_pt"] + n.loc[(a, turno), "votos_antipt"]) for a in v.ano]
    return float(np.sqrt(((v.pt / (v.pt + v.rival) - real) ** 2).mean())), len(v)


def preparar(csv="datasets/pesquisas-2026.csv"):
    d = pd.read_csv(csv, parse_dates=["campo_ini", "campo_fim", "divulgacao"])
    d["data"] = d.campo_ini + (d.campo_fim - d.campo_ini) / 2
    d["data"] = d.data.fillna(d.divulgacao)
    d["n"] = d.amostra.fillna(2000)
    cands = ["t1_lula", "t1_flavio", "t1_caiado", "t1_zema", "t1_renan", "t1_cury", "t1_outros"]
    completo = d[cands].notna().all(axis=1)
    d["p1"] = np.where(completo, d.t1_lula / d[cands].sum(axis=1), np.nan)
    d["p2"] = d.t2_lula / (d.t2_lula + d.t2_flavio)
    d["p1s"] = d.t1_lula / (d.t1_lula + d.t1_flavio)                       # Lula/(Lula+Flávio), 1º turno
    d["q"] = np.where(completo, (d.t1_lula + d.t1_flavio) / d[cands].sum(axis=1), np.nan)  # Lula+Flávio nos válidos
    return d


def estimar(df, col, hoje=HOJE, tau=TAU_DIAS, sd_vies=SD_VIES_HIST, h_dias=0):
    """Retorna (p, sd_logit, house_effects, n_pesquisas)."""
    d = df.dropna(subset=[col]).copy()
    p = d[col].to_numpy()
    inst = sorted(d.instituto.unique())
    k = len(inst)
    dias = (d.data - hoje).dt.days.to_numpy(float)          # ≤ 0
    X = np.column_stack([np.ones(len(d)), dias / 30] +
                        [(d.instituto == i).astype(float) - (d.instituto == inst[-1]).astype(float)
                         for i in inst[:-1]])
    var = 1 / (d.n.to_numpy() / DEFF * p * (1 - p))        # variância de logit(p)
    w = np.exp(dias / tau) / var
    A = np.linalg.inv(X.T @ (w[:, None] * X))
    beta = A @ X.T @ (w * logit(p))
    cov = A @ (X.T @ ((w * w * var)[:, None] * X)) @ A      # sanduíche: pesos ≠ 1/var
    h = np.append(beta[2:], -beta[2:].sum())
    var_inst = h.var(ddof=1) / k if k > 1 else 0.0          # incerteza de qual conjunto de institutos
    var_drift = (h_dias / 30) ** 2 * cov[1, 1]               # incerteza da tendência até a eleição (média sem extrapolar)
    sd = np.sqrt(cov[0, 0] + var_inst + var_drift + (sd_vies / (p.mean() * (1 - p.mean()))) ** 2)
    return 1 / (1 + np.exp(-beta[0])), sd, {i: round(float(x), 4) for i, x in zip(inst, h)}, len(d)


def evolucao(datas, csv="datasets/pesquisas-2026.csv"):
    """Parâmetros do modelo "como estava em" cada data (só pesquisas até aquela data), para o gráfico de evolução.
    Retorna [{data, s, q, sd_s, sd_q, s2, sd2, n1, n2}]; datas com pesquisas insuficientes para o ajuste são puladas.
    ponytail: usa o viés histórico de hoje (RMSE) retroativamente; horizonte = dias até 4/10 (1º) e 25/10 (2º) a partir da data."""
    d, sv1, sv2 = preparar(csv), vies_rmse(1)[0], vies_rmse(2)[0]
    out = []
    for t in map(pd.Timestamp, datas):
        x = d[d.data <= t]
        try:
            s, sds, _, n1 = estimar(x, "p1s", hoje=t, sd_vies=sv1, h_dias=(pd.Timestamp("2026-10-04") - t).days)
            q, sdq, _, _ = estimar(x, "q", hoje=t, h_dias=(pd.Timestamp("2026-10-04") - t).days)
            s2, sd2, _, n2 = estimar(x, "p2", hoje=t, sd_vies=sv2, h_dias=(pd.Timestamp("2026-10-25") - t).days)
        except np.linalg.LinAlgError:
            continue
        if min(n1, n2) >= 8 and np.isfinite([s, q, s2, sds, sdq, sd2]).all():
            out.append(dict(data=str(t.date()), s=round(float(s), 4), q=round(float(q), 4), sd_s=round(float(sds), 4), sd_q=round(float(sdq), 4),
                            s2=round(float(s2), 4), sd2=round(float(sd2), 4), n1=int(n1), n2=int(n2)))
    return out


def main(saida="modelos/parametros.json"):
    d = preparar()
    out = {"data_referencia": str(HOJE.date())}
    for turno, col in ((1, "p1"), (2, "p2")):
        sv, nv = vies_rmse(turno)
        p, sd, h, n = estimar(d, col, sd_vies=sv, h_dias=HORIZONTE[turno])
        out[f"turno{turno}"] = dict(p_pesquisas=round(p, 4), sd_logit=round(sd, 4),
                                    delta=round(logit(p) - logit(P2022[turno]), 4),
                                    p_2022=P2022[turno], house_effects_logit=h, n_pesquisas=n,
                                    sd_vies_hist=round(sv, 4), n_vies=nv)
        lo, hi = (1 / (1 + np.exp(-(logit(p) + s * 1.645 * sd))) for s in (-1, 1))
        print(f"{turno}º turno: Lula {p:.1%} (90%: {lo:.1%}–{hi:.1%}) | δ={out[f'turno{turno}']['delta']:+.3f} "
              f"| sd_logit={sd:.3f} | viés hist. RMSE={sv:.1%} (n={nv}) | n={n}\n   house effects (logit): {h}")
    antigo = json.loads(Path(saida).read_text()) if Path(saida).exists() else {}
    if "mc" in antigo:                      # parâmetros do Monte Carlo (montecarlo.py) não podem se perder
        out["mc"] = antigo["mc"]
    Path(saida).write_text(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

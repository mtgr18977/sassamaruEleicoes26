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
    return d


def estimar(df, col, hoje=HOJE, tau=TAU_DIAS, sd_vies=SD_VIES_HIST):
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
    sd = np.sqrt(cov[0, 0] + var_inst + (sd_vies / (p.mean() * (1 - p.mean()))) ** 2)
    return 1 / (1 + np.exp(-beta[0])), sd, {i: round(float(x), 4) for i, x in zip(inst, h)}, len(d)


def main(saida="modelos/parametros.json"):
    d = preparar()
    out = {"data_referencia": str(HOJE.date())}
    for turno, col in ((1, "p1"), (2, "p2")):
        sv, nv = vies_rmse(turno)
        p, sd, h, n = estimar(d, col, sd_vies=sv)
        out[f"turno{turno}"] = dict(p_pesquisas=round(p, 4), sd_logit=round(sd, 4),
                                    delta=round(logit(p) - logit(P2022[turno]), 4),
                                    p_2022=P2022[turno], house_effects_logit=h, n_pesquisas=n,
                                    sd_vies_hist=round(sv, 4), n_vies=nv)
        lo, hi = (1 / (1 + np.exp(-(logit(p) + s * 1.645 * sd))) for s in (-1, 1))
        print(f"{turno}º turno: Lula {p:.1%} (90%: {lo:.1%}–{hi:.1%}) | δ={out[f'turno{turno}']['delta']:+.3f} "
              f"| sd_logit={sd:.3f} | viés hist. RMSE={sv:.1%} (n={nv}) | n={n}\n   house effects (logit): {h}")
    Path(saida).write_text(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

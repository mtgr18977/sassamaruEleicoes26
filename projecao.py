"""Projeção do 1º turno de 2026 (Lula × Flávio × demais), base = distribuição por UF em 2022.

Dois eixos em logit, cada um com swing uniforme + choque regional + ruído por UF (medidos 2002–2022):
  s = Lula/(Lula+Flávio)  (lulismo × bolsonarismo)     q = (Lula+Flávio)/válidos  (peso da terceira via)
Total nacional de cada eixo vem das pesquisas (house effect, recência, viés histórico). Flávio = bloco anti-PT de 2022.
Cenário "viés se repete": desloca s pelo erro médio das pesquisas finais (+3 p.p. a favor do PT em 2002/2018/2022).
"""
import json
import numpy as np
import pandas as pd
from backtest import D, inv, logit
from nivel2 import REGIAO
from pesquisas import estimar, preparar, vies_rmse, SD_VIES_HIST

REGIAO["ZZ"] = "EX"
N, rng = 20000, np.random.default_rng(2026)


def ruido(uf, num, den):
    """(sd choque regional, sd ruído UF) em logit de num/den, resíduos do swing uniforme entre eleições consecutivas."""
    uf = uf[(uf.turno == 1) & ~uf.uf.isin(["ZZ", "VT"])].copy()
    uf["y"] = logit((uf[num] / uf[den]).clip(1e-4, 1 - 1e-4))
    res = []
    for a, b in zip(sorted(uf.ano.unique())[:-1], sorted(uf.ano.unique())[1:]):
        x, y = uf[uf.ano == a].set_index("uf"), uf[uf.ano == b].set_index("uf")
        i = x.index.intersection(y.index)
        dy = y.loc[i, "y"] - x.loc[i, "y"]
        w = y.loc[i, den]
        res.append(pd.DataFrame({"r": dy - (dy * w).sum() / w.sum(), "g": [REGIAO[u] for u in i]}))
    r = pd.concat(res, keys=range(len(res))).reset_index()
    g = r.groupby(["level_0", "g"]).r
    var_uf = g.var(ddof=1).mean()
    return float(np.sqrt(max(g.mean().var(ddof=1) - (var_uf / g.size()).mean(), 0))), float(np.sqrt(var_uf))


def calibrar(y, w, alvo):
    lo, hi = np.full(len(alvo), -4.0), np.full(len(alvo), 4.0)
    for _ in range(50):
        m = (lo + hi) / 2
        baixo = (inv(y + m[:, None]) @ w) < alvo
        lo, hi = np.where(baixo, m, lo), np.where(baixo, hi, m)
    return (lo + hi) / 2


def simular(u, s_nac, sd_s, q_nac, sd_q, rs, qs):
    """u: UFs 2022 com s0, q0, w. rs/qs = (sd_reg, sd_uf) dos eixos s e q."""
    k, w = len(u), (u.validos / u.validos.sum()).to_numpy()
    regs = sorted(set(u.regiao)); idx = np.array([regs.index(r) for r in u.regiao])
    sn = inv(logit(s_nac) + sd_s * rng.standard_normal(N))
    qn = inv(logit(q_nac) + sd_q * rng.standard_normal(N))
    ruido_ = lambda sd: sd[0] * rng.standard_normal((N, len(regs)))[:, idx] + sd[1] * rng.standard_normal((N, k))
    yq = logit(u.q0.to_numpy()) + ruido_(qs)
    q = inv(yq + calibrar(yq, w, qn)[:, None])
    ys = logit(u.s0.to_numpy()) + ruido_(rs)
    lo, hi = np.full(N, -4.0), np.full(N, 4.0)                       # s ponderado por Lula+Flávio de cada UF
    for _ in range(50):
        m = (lo + hi) / 2
        s_ = inv(ys + m[:, None]); baixo = ((q * s_) @ w) / (q @ w) < sn
        lo, hi = np.where(baixo, m, lo), np.where(baixo, hi, m)
    s = inv(ys + ((lo + hi) / 2)[:, None])
    L, F = q * s, q * (1 - s)
    return L, F, 1 - q


def resumo(L, F, O):
    ln, fn, on = L @ W, F @ W, O @ W
    pc = lambda x: np.percentile(x, [5, 50, 95]) * 100
    return dict(L=pc(ln), F=pc(fn), O=pc(on), p_lula_a_frente=float((ln > fn).mean()), p_lula_gt50=float((ln > .5).mean()),
                p_flavio_gt50=float((fn > .5).mean()), p_2turno=float(((ln <= .5) & (fn <= .5)).mean()),
                p_lf_2turno=float((np.minimum(ln, fn) > on).mean()),   # cota: todos os demais como UM candidato
                margem=pc(ln - fn))


if __name__ == "__main__":
    par = json.load(open("modelos/parametros.json"))
    d = preparar()
    sv, _ = vies_rmse(1)
    s_nac, sd_s, _, _ = estimar(d, "p1s", sd_vies=sv)
    q_nac, sd_q, _, _ = estimar(d, "q", sd_vies=SD_VIES_HIST)       # ponytail: viés da terceira via não medido (2 p.p. assumidos)
    uf = pd.read_csv(D + "tse-presidente-uf.csv")
    rs, qs = ruido(uf.assign(num=uf.votos_pt, den=uf.votos_pt + uf.votos_antipt), "num", "den"), \
        ruido(uf.assign(num=uf.votos_pt + uf.votos_antipt), "num", "validos")
    u = uf[(uf.ano == 2022) & (uf.turno == 1) & (uf.uf != "VT")].reset_index(drop=True)
    u["s0"] = u.votos_pt / (u.votos_pt + u.votos_antipt); u["q0"] = (u.votos_pt + u.votos_antipt) / u.validos
    u["regiao"] = u.uf.map(REGIAO)
    W = (u.validos / u.validos.sum()).to_numpy()
    bias = 0.03                                                       # erro médio das pesquisas finais (vies-pesquisas.csv, turno 1)
    print(f"s=Lula/(L+F): {s_nac:.3f} (sd {sd_s:.3f}) | q=L+F: {q_nac:.3f} (sd {sd_q:.3f}) | ruído s (reg,uf) {rs[0]:.2f},{rs[1]:.2f} | q {qs[0]:.2f},{qs[1]:.2f}")
    out = {"data": "2026-10-01"}
    for nome, s0 in (("pesquisas", s_nac), ("vies_se_repete", float(inv(logit(s_nac) - 0)) - bias)):
        L, F, O = simular(u, s0, sd_s, q_nac, sd_q, rs, qs)
        r = resumo(L, F, O)
        out[nome] = {k: (np.round(v, 1).tolist() if isinstance(v, np.ndarray) else round(v, 4)) for k, v in r.items()}
        q5 = lambda x: np.percentile(x, [5, 50, 95], axis=0) * 100
        t = pd.DataFrame({"uf": u.uf, "lula_2022": u.pct_pt_validos, "bolsonaro_2022": u.pct_antipt_validos, "outros_2022": u.pct_outros_validos,
                          "lula": q5(L)[1], "flavio": q5(F)[1], "outros": q5(O)[1], "margem_p5": q5(L - F)[0], "margem": q5(L - F)[1],
                          "margem_p95": q5(L - F)[2], "P(Lula à frente)": (L > F).mean(0) * 100})
        t.sort_values("margem", ascending=False).round(1).to_csv(f"modelos/projecao-1turno-uf-{nome}.csv", index=False)
        out[nome]["ufs_lula_a_frente"] = round(float((L > F).mean(0).sum()), 1)
        out[nome]["ufs"] = t.sort_values("margem", ascending=False).round(1).to_dict("records")
        print(f"\n=== {nome} (Lula/(L+F) = {s0:.3f}) ===")
        for k in ("L", "F", "O", "margem"):
            print(f"{k:>7}: mediana {out[nome][k][1]:5.1f}   IC90 {out[nome][k][0]:5.1f} – {out[nome][k][2]:5.1f}")
        print({k: out[nome][k] for k in ("p_lula_a_frente", "p_lula_gt50", "p_flavio_gt50", "p_2turno", "ufs_lula_a_frente")})
    json.dump(out, open("modelos/projecao-1turno.json", "w"), ensure_ascii=False)

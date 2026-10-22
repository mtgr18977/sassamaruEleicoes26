"""Gera historico.html (aba "Histórico": o Lula de 2002 a 2026 por região e capital, pesquisas × resultado e simulador do 2º turno; autocontida, dados embutidos) a partir dos CSVs.
Lula = 2002, 2006, 2022 e 2026 (só o 1º turno, que o TSE já publicou; o 2º turno é em 25/10). Eleições sem Lula na urna (2010/2014 Dilma, 2018 Haddad) ficam como pontos de contexto."""
import json

import nav
import numpy as np
import pandas as pd
from nivel2 import REGIAO

D = "datasets/"
CAND = {2002: "Lula", 2006: "Lula", 2010: "Dilma", 2014: "Dilma", 2018: "Haddad", 2022: "Lula", 2026: "Lula"}
COM_LULA = (2002, 2006, 2022, 2026)
RIVAL = {2002: "Serra", 2006: "Alckmin", 2010: "Serra", 2014: "Aécio", 2018: "Bolsonaro", 2022: "Bolsonaro", 2026: "Flávio"}
r1 = lambda x: None if pd.isna(x) else round(float(x), 2)

nac = pd.read_csv(D + "tse-presidente-nacional.csv")
uf = pd.read_csv(D + "tse-presidente-uf.csv")
uf = uf[~uf.uf.isin(["ZZ", "VT"])].assign(reg=lambda d: d.uf.map(REGIAO))
mun = pd.read_csv(D + "tse-presidente-municipio.csv", dtype={"cod_municipio": str})
mun = mun[~mun.uf.isin(["ZZ", "VT"])]
cap = pd.read_csv(D + "tse-presidente-capitais.csv")

out = {"cand": CAND, "rival": RIVAL}
out["nac"] = [dict(ano=int(r.ano), turno=int(r.turno), pt=r1(r.pct_pt_validos), anti=r1(r.pct_antipt_validos),
                   votos=int(r.votos_pt), cand=CAND[r.ano], rival=RIVAL[r.ano], lula=bool(r.ano in COM_LULA))
              for r in nac.itertuples()]
# 2026 ainda não tem 2º turno: linha vazia, para os gráficos deixarem o ponto em branco
out["nac"] += [dict(ano=a, turno=t, pt=None, anti=None, votos=None, cand=CAND[a], rival=RIVAL[a], lula=a in COM_LULA)
               for a in CAND for t in (1, 2) if not ((nac.ano == a) & (nac.turno == t)).any()]

reg, share, heat, cvi, caps = {}, {}, {}, {}, {}
REGS = ["N", "NE", "CO", "SE", "S"]
UFS = sorted(uf.uf.unique())
for t in (1, 2):
    ut = uf[uf.turno == t]
    g = ut.groupby(["ano", "reg"])[["votos_pt", "validos"]].sum()
    tem = lambda a: bool(((uf.ano == a) & (uf.turno == t)).any())     # 2026 ainda não tem 2º turno: fica em branco (None)
    reg[t] = {str(a): {r: r1(100 * g.loc[(a, r), "votos_pt"] / g.loc[(a, r), "validos"]) if tem(a) else None for r in REGS} for a in CAND}
    share[t] = {str(a): {r: r1(100 * g.loc[(a, r), "votos_pt"] / g.loc[a].votos_pt.sum()) if tem(a) else None for r in REGS} for a in CAND}
    heat[t] = {str(a): ({u: r1(v) for u, v in ut[ut.ano == a].set_index("uf").pct_pt_validos.items()} if tem(a) else {u: None for u in UFS})
               for a in CAND}
    mt = mun[mun.turno == t]
    cvi[t] = {}
    for a in CAND:
        m = mt[mt.ano == a]
        f = lambda d: r1(100 * d.votos_pt.sum() / d.validos.sum()) if len(d) else None
        cvi[t][str(a)] = dict(capitais=f(m[m.eh_capital]), interior=f(m[~m.eh_capital]), brasil=f(m))
    caps[t] = {}
    for a in CAND:
        c = cap[(cap.ano == a) & (cap.turno == t)].set_index("uf")
        s = uf[(uf.ano == a) & (uf.turno == t)].set_index("uf")
        caps[t][str(a)] = sorted([dict(uf=u, capital=c.loc[u, "municipio"].title(), cap=r1(c.loc[u, "pct_pt_validos"]),
                                       uf_pct=r1(s.loc[u, "pct_pt_validos"])) for u in c.index], key=lambda x: -x["cap"])
out.update(reg=reg, share=share, heat=heat, cvi=cvi, caps=caps)

# pesquisas × resultado
v = pd.read_csv(D + "vies-pesquisas.csv")
real = {(a, t): nac[(nac.ano == a) & (nac.turno == t)].iloc[0] for a, t in {(r.ano, r.turno) for r in v.itertuples()}}
out["vies"] = [dict(ano=int(r.ano), turno=int(r.turno), inst=r.instituto, cand=CAND[r.ano], rival=RIVAL[r.ano],
                    pesq=r1(100 * r.pt / (r.pt + r.rival)),
                    real=r1(100 * real[(r.ano, r.turno)].votos_pt / (real[(r.ano, r.turno)].votos_pt + real[(r.ano, r.turno)].votos_antipt)),
                    lula=bool(r.ano in (2002, 2006, 2022))) for r in v.itertuples()]
for x in out["vies"]:
    x["erro"] = r1(x["pesq"] - x["real"])
# 2026: última pesquisa de 1º turno de cada um dos 16 institutos antes da votação (4/10), contra o resultado do TSE (erros_1turno.py)
import erros_1turno
_t = erros_1turno.tabela()
_real = round(erros_1turno.resultado()[0], 2)
out["vies"] += [dict(ano=2026, turno=1, inst=i, cand="Lula", rival="Flávio", pesq=round(float(r.erro) + _real, 2), real=_real, lula=True,
                     erro=round(float(r.erro), 2), atlas=bool(r.origem == "atlas")) for i, r in _t.iterrows()]

p = pd.read_csv(D + "pesquisas-2026.csv")
p["data"] = pd.to_datetime(p.campo_fim).fillna(pd.to_datetime(p.divulgacao))
out["pesq26"] = [dict(inst=r.instituto, data=str(r.data.date()),
                      s1=r1(100 * r.t1_lula / (r.t1_lula + r.t1_flavio)), l1=r1(r.t1_lula), f1=r1(r.t1_flavio),
                      s2=r1(100 * r.t2_lula / (r.t2_lula + r.t2_flavio)) if pd.notna(r.t2_lula) else None,
                      l2=r1(r.t2_lula), f2=r1(r.t2_flavio)) for r in p.sort_values("data").itertuples()]
out["proj"] = {k: v for k, v in json.load(open("modelos/projecao-1turno.json")).items() if k != "data"}
# parâmetros do simulador interativo (projecao-model.js)
import projecao
from pesquisas import HOJE_1T, P2022, estimar, preparar, vies_eleicao, vies_rmse, SD_VIES_HIST, SD_PISO_2T_PP
_d, _sv = preparar(), vies_rmse(1)[0]
_s, _sds, _, _ = estimar(_d, "p1s", hoje=HOJE_1T, sd_vies=_sv)
_q, _sdq, _, _ = estimar(_d, "q", hoje=HOJE_1T, sd_vies=SD_VIES_HIST)
_u = uf_all = pd.read_csv(D + "tse-presidente-uf.csv")
_rs = projecao.ruido(_u.assign(num=_u.votos_pt, den=_u.votos_pt + _u.votos_antipt), "num", "den")
_qs = projecao.ruido(_u.assign(num=_u.votos_pt + _u.votos_antipt), "num", "validos")
_b = _u[(_u.ano == 2022) & (_u.turno == 1) & (_u.uf != "VT")]
out["projmodel"] = dict(s=round(float(_s), 4), q=round(float(_q), 4), sd_s=round(float(_sds), 4), sd_q=round(float(_sdq), 4),
                        ruido=dict(s=[round(x, 4) for x in _rs], q=[round(x, 4) for x in _qs]),
                        ufs=[dict(uf=r.uf, regiao=("EX" if r.uf == "ZZ" else REGIAO[r.uf]), s0=round(r.votos_pt / (r.votos_pt + r.votos_antipt), 6),
                                  q0=round((r.votos_pt + r.votos_antipt) / r.validos, 6), w=int(r.validos)) for r in _b.itertuples()],
                        vies_medio={t: round(vies_eleicao(t)[0], 2) for t in (1, 2)}, vies_n_eleicoes={t: vies_eleicao(t)[1] for t in (1, 2)})
import validar_regioes
out["piso2t"] = SD_PISO_2T_PP
_r = pd.read_csv(D + "resultado-2026-turno1.csv").query("uf == 'BR'").iloc[0]
out["r1t_s"] = round(100 * float(_r.lula) / (float(_r.lula) + float(_r.flavio)), 2)   # Lula/(Lula+Flávio) no 1º turno realizado
out["p2022_2t"] = round(100 * P2022[2], 2)
out["valreg"] = validar_regioes.comparar()
out["modelo"] = json.load(open("modelos/parametros.json"))

html = nav.moldura(open("apps/lula.template.html", encoding="utf-8").read(), "historico.html").replace("__DATA__", json.dumps(out, ensure_ascii=False))
open("historico.html", "w", encoding="utf-8").write(html)
print("historico.html", len(html) // 1024, "KB")

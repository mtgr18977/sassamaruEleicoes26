"""Gera apps/lula.html (autocontida, dados embutidos) a partir dos CSVs.
Lula = 2002, 2006, 2022. Eleições sem Lula na urna (2010/2014 Dilma, 2018 Haddad) ficam como pontos de contexto."""
import json
import numpy as np
import pandas as pd
from nivel2 import REGIAO

D = "datasets/"
CAND = {2002: "Lula", 2006: "Lula", 2010: "Dilma", 2014: "Dilma", 2018: "Haddad", 2022: "Lula"}
RIVAL = {2002: "Serra", 2006: "Alckmin", 2010: "Serra", 2014: "Aécio", 2018: "Bolsonaro", 2022: "Bolsonaro"}
r1 = lambda x: None if pd.isna(x) else round(float(x), 2)

nac = pd.read_csv(D + "tse-presidente-nacional.csv")
uf = pd.read_csv(D + "tse-presidente-uf.csv")
uf = uf[~uf.uf.isin(["ZZ", "VT"])].assign(reg=lambda d: d.uf.map(REGIAO))
mun = pd.read_csv(D + "tse-presidente-municipio.csv", dtype={"cod_municipio": str})
mun = mun[~mun.uf.isin(["ZZ", "VT"])]
cap = pd.read_csv(D + "tse-presidente-capitais.csv")

out = {"cand": CAND, "rival": RIVAL}
out["nac"] = [dict(ano=int(r.ano), turno=int(r.turno), pt=r1(r.pct_pt_validos), anti=r1(r.pct_antipt_validos),
                   votos=int(r.votos_pt), cand=CAND[r.ano], rival=RIVAL[r.ano], lula=bool(r.ano in (2002, 2006, 2022)))
              for r in nac.itertuples()]

reg, share, heat, cvi, caps = {}, {}, {}, {}, {}
for t in (1, 2):
    ut = uf[uf.turno == t]
    g = ut.groupby(["ano", "reg"])[["votos_pt", "validos"]].sum()
    reg[t] = {str(a): {r: r1(100 * g.loc[(a, r), "votos_pt"] / g.loc[(a, r), "validos"]) for r in ["N", "NE", "CO", "SE", "S"]}
              for a in CAND}
    share[t] = {str(a): {r: r1(100 * g.loc[(a, r), "votos_pt"] / g.loc[a].votos_pt.sum()) for r in ["N", "NE", "CO", "SE", "S"]}
                for a in CAND}
    heat[t] = {str(a): {u: r1(v) for u, v in ut[ut.ano == a].set_index("uf").pct_pt_validos.items()} for a in CAND}
    mt = mun[mun.turno == t]
    cvi[t] = {}
    for a in CAND:
        m = mt[mt.ano == a]
        f = lambda d: r1(100 * d.votos_pt.sum() / d.validos.sum())
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

p = pd.read_csv(D + "pesquisas-2026.csv")
p["data"] = pd.to_datetime(p.campo_fim).fillna(pd.to_datetime(p.divulgacao))
out["pesq26"] = [dict(inst=r.instituto, data=str(r.data.date()),
                      s1=r1(100 * r.t1_lula / (r.t1_lula + r.t1_flavio)), l1=r1(r.t1_lula), f1=r1(r.t1_flavio),
                      s2=r1(100 * r.t2_lula / (r.t2_lula + r.t2_flavio)) if pd.notna(r.t2_lula) else None,
                      l2=r1(r.t2_lula), f2=r1(r.t2_flavio)) for r in p.sort_values("data").itertuples()]
out["modelo"] = json.load(open("modelos/parametros.json"))
for k in ("mc",):
    out["modelo"].pop(k, None)

html = open("apps/lula.template.html", encoding="utf-8").read().replace("__DATA__", json.dumps(out, ensure_ascii=False))
open("apps/lula.html", "w", encoding="utf-8").write(html)
print("apps/lula.html", len(html) // 1024, "KB")

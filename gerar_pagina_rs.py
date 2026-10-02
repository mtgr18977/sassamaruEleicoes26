"""Gera rs.html (aba do governo do RS; dados embutidos) a partir de apps/rs.template.html."""
import json

import numpy as np
import pandas as pd

import rs_modelo as rm
from rs_dados import ESQ, NOME_UNIDADE, blocos_por_unidade, carregar

NOMES_INST = {"ParanaPesquisas": "Paraná Pesquisas", "RealTimeBigData": "Real Time Big Data", "AtlasIntel": "AtlasIntel", "Quaest": "Quaest", "Neokemp": "Neokemp"}
r2 = lambda x: None if pd.isna(x) else round(float(x), 2)

m = carregar()
out = {}
# --- histórico (TSE) ---
cand = m.groupby(["ano", "turno", "nome", "partido", "bloco"], as_index=False).votos.sum()
cand["pct"] = 100 * cand.votos / cand.groupby(["ano", "turno"]).votos.transform("sum")
out["cand"] = {str(a): {str(t): [dict(nome=r.nome.title().replace(" De ", " de ").replace(" Da ", " da "), partido=r.partido, bloco=r.bloco, pct=r2(r.pct)) for r in g.sort_values("pct", ascending=False).itertuples() if r.pct >= 1]
                       for t, g in gg.groupby("turno")} for a, gg in cand.groupby("ano")}
est = m[m.turno == 1].groupby(["ano", "bloco"]).votos.sum().unstack()
est = 100 * est.div(est.sum(axis=1), axis=0)
out["blocos"] = {str(a): {b: r2(est.loc[a, b]) for b in "ECD"} for a in est.index}
u = blocos_por_unidade(m)
out["unidades"] = {str(a): {r.unidade_nome: {b: r2(100 * getattr(r, b)) for b in "ECD"} for r in g.itertuples()} for a, g in u.groupby("ano")}
cv = {}
for b in "ECD":
    cv[b] = {}
    for a, g in m[m.turno == 1].groupby("ano"):
        f = lambda d: r2(100 * d[d.bloco == b].votos.sum() / d.votos.sum())
        cv[b][str(a)] = dict(capital=f(g[g.unidade_nome == "Porto Alegre"]), interior=f(g[g.unidade_nome != "Porto Alegre"]), estado=f(g))
out["cvi"] = cv
# --- pesquisas 2026 ---
d = rm.preparar()
out["polls"] = [dict(inst=NOMES_INST[r.instituto], instk=r.instituto, data=str(r.data.date()), amostra=int(r.amostra), registro=r.registro,
                     z=r2(100 * r.z3 * (1 - r.r)), b=r2(100 * r.b3 * (1 - r.r)), s=r2(100 * r.s3 * (1 - r.r)), r=r2(100 * r.r),
                     zb2=r2(100 * r.r2_zb_z / (r.r2_zb_z + r.r2_zb_b)) if pd.notna(r.r2_zb_z) else None,
                     zs2=r2(100 * r.r2_zs_z / (r.r2_zs_z + r.r2_zs_s)) if pd.notna(r.r2_zs_z) else None,
                     bs2=r2(100 * r.r2_bs_b / (r.r2_bs_b + r.r2_bs_s)) if pd.notna(r.r2_bs_b) else None,
                     zucco=r2(r.zucco), brizola=r2(r.brizola), souza=r2(r.souza)) for r in d.sort_values("data").itertuples()]
# --- modelo ---
par = rm.parametros(d)
ev = []
for t in sorted({*pd.date_range("2026-08-27", "2026-10-02", freq="7D"), pd.Timestamp("2026-10-02")}):
    try:
        p = rm.parametros(d, t)
    except np.linalg.LinAlgError:
        continue
    if p["n"] >= 3 and min(v["n"] for v in p["pares"].values()) >= 2:
        ev.append(dict(data=str(t.date()), par=p))
out["modelo"] = dict(par=par, evolucao=ev, unidades=rm.unidades().to_dict("records"), sigma=rm.ruido_unidade(), rho=rm.RHO, piso2t=rm.SD_PISO_2T_PP, sistematico1t=rm.SISTEMATICO_1T_PP)
out["nomes_unidade"] = NOME_UNIDADE
import agregador
out["agg"] = agregador.rs()
html = open("apps/rs.template.html", encoding="utf-8").read().replace("__DATA__", json.dumps(out, ensure_ascii=False))
open("rs.html", "w", encoding="utf-8").write(html)
print("rs.html", len(html) // 1024, "KB |", len(ev), "pontos de evolução")

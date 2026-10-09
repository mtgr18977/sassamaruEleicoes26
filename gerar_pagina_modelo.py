"""Gera analise-modelo.html (aba "Análise do modelo": o que eu previ × o que aconteceu no 1º turno de 2026) a partir de apps/analise-modelo.template.html.

Cobre três disputas já decididas: Presidente (1º turno), Governador do RS e bancada do RS (federal e estadual). As previsões são as CONGELADAS de 2/10
(modelos/projecao-1turno.json, rs_modelo.py com HOJE = 2/10, rs_bancada.py), os resultados vêm de datasets/resultado-2026-*.csv (preliminares, com a fonte de cada linha).
O 2º turno presidencial ainda não tem resultado: aparece só a previsão atual, para ser avaliada em 25/10. Reaproveita os dados de gerar_paginas_analise_rs.py."""
import json
import math

import pandas as pd

import nav
from gerar_paginas_analise_rs import bancada, governo
from pesquisas import vies_eleicao

D = "datasets/"
res = pd.read_csv(D + "resultado-2026-turno1.csv")
br = res[res.uf == "BR"].iloc[0]
L26, F26 = float(br.lula), float(br.flavio)
O26 = round(100 - L26 - F26, 2)

# ---------------------------------------------------------------- Presidente, 1º turno
pj = json.load(open("modelos/projecao-1turno.json"))
cen = {k: pj[k] for k in ("pesquisas", "vies_se_repete")}
presidente = dict(
    data=pj["data"], real=dict(L=L26, F=F26, O=O26, margem=round(L26 - F26, 2)),
    cen={k: dict(L=v["L"], F=v["F"], O=v["O"], margem=v["margem"]) for k, v in cen.items()},
    prob=dict(segundo_turno=pj["pesquisas"]["p_2turno"], lula_a_frente=pj["pesquisas"]["p_lula_a_frente"], lula_gt50=pj["pesquisas"]["p_lula_gt50"], flavio_gt50=pj["pesquisas"]["p_flavio_gt50"]))
p = pd.read_csv(D + "pesquisas-2026.csv").sort_values("campo_fim").dropna(subset=["t1_lula", "t1_flavio"])
ult = p.groupby("instituto").tail(1)
real_s = 100 * float(br.votos_lula) / (float(br.votos_lula) + float(br.votos_flavio))
presidente["pesq"] = [dict(inst=r.instituto, campo=r.campo_fim, base=r.base, s=round(100 * r.t1_lula / (r.t1_lula + r.t1_flavio), 1)) for r in ult.itertuples()]
presidente["real_s"] = round(real_s, 2)
presidente["vies_hist"] = round(vies_eleicao(1)[0], 2)

proj_uf = pd.read_csv("modelos/projecao-1turno-uf-pesquisas.csv").set_index("uf")
ufs = []
for r in res[res.uf != "BR"].itertuples():
    if r.uf not in proj_uf.index:
        continue
    a = proj_uf.loc[r.uf]
    ufs.append(dict(uf=r.uf, L_prev=float(a.lula), F_prev=float(a.flavio), L=None if pd.isna(r.lula) else float(r.lula), F=None if pd.isna(r.flavio) else float(r.flavio)))
presidente["ufs"] = ufs
erros = [abs(u["L"] - u["L_prev"]) for u in ufs if u["L"] is not None] + [abs(u["F"] - u["F_prev"]) for u in ufs if u["F"] is not None]
presidente["mae_uf"] = round(sum(erros) / len(erros), 2) if erros else None
presidente["n_uf"] = len(erros)

# 2º turno: só a previsão atual (sem resultado)
par = json.load(open("modelos/parametros.json"))["turno2"]
Phi = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
presidente["t2"] = dict(s=round(100 * par["p_pesquisas"], 2), sd=par["sd_logit"], lula=round(Phi(math.log(par["p_pesquisas"] / (1 - par["p_pesquisas"])) / par["sd_logit"]), 4),
                        data=json.load(open("modelos/parametros.json"))["data_referencia"])

out = dict(presidente=presidente, governo=governo(), bancada=bancada())
html = nav.moldura(open("apps/analise-modelo.template.html", encoding="utf-8").read(), "analise-modelo.html").replace("__DATA__", json.dumps(out, ensure_ascii=False))
open("analise-modelo.html", "w", encoding="utf-8").write(html)
print("analise-modelo.html", len(html) // 1024, "KB")

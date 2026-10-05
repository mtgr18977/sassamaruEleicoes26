"""Gera analise.html (aba Análise do 1º turno de 2026; dados embutidos) a partir de apps/analise.template.html.

Entradas: datasets/resultado-2026-turno1.csv (resultado preliminar, com a fonte de cada linha), TSE 2022 (datasets/tse-presidente-*.csv),
pesquisas-2026.csv e modelos/projecao-1turno.json (projeção de 2/10). Só mostra número com fonte; célula vazia = não localizei."""
import json

import pandas as pd

from pesquisas import vies_eleicao

D = "datasets/"
nac = pd.read_csv(D + "tse-presidente-nacional.csv").query("ano == 2022 and turno == 1").iloc[0]
res = pd.read_csv(D + "resultado-2026-turno1.csv")
br = res[res.uf == "BR"].iloc[0]
L26, F26 = float(br.lula), float(br.flavio)
O26 = round(100 - L26 - F26, 2)
v26 = br.votos_flavio / (F26 / 100)           # válidos de 2026, derivados dos votos e do % divulgados

out = dict(
    r26=dict(L=L26, F=F26, O=O26, vL=int(br.votos_lula), vF=int(br.votos_flavio), validos=round(v26), fonte=br.fonte, obs=br.obs),
    r22=dict(L=round(nac.pct_pt_validos, 2), F=round(nac.pct_antipt_validos, 2), O=round(nac.pct_outros_validos, 2),
             vL=int(nac.votos_pt), vF=int(nac.votos_antipt), vO=int(nac.votos_outros), validos=int(nac.validos)))

out["r22"]["L2"] = round(float(pd.read_csv(D + "tse-presidente-nacional.csv").query("ano == 2022 and turno == 2").iloc[0].pct_pt_validos), 2)

# projeção de 2/10 × resultado (válidos)
pj = json.load(open("modelos/projecao-1turno.json"))
out["proj"] = {k: dict(L=pj[k]["L"], F=pj[k]["F"], O=pj[k]["O"], margem=pj[k]["margem"]) for k in ("pesquisas", "vies_se_repete")}
out["proj_data"] = pj["data"]

# última pesquisa de cada instituto antes do 1º turno, na parcela Lula/(Lula+Flávio) (mesma da calibração de viés do modelo)
p = pd.read_csv(D + "pesquisas-2026.csv").sort_values("campo_fim").dropna(subset=["t1_lula", "t1_flavio"])
ult = p.groupby("instituto").tail(1)
out["pesq"] = [dict(inst=r.instituto, campo=r.campo_fim, base=r.base, L=r.t1_lula, F=r.t1_flavio,
                    s=round(100 * r.t1_lula / (r.t1_lula + r.t1_flavio), 1)) for r in ult.itertuples()]
out["real_s"] = round(100 * br.votos_lula / (br.votos_lula + br.votos_flavio), 2)
out["vies_hist"] = round(vies_eleicao(1)[0], 2)

# UFs com número publicado
u22 = pd.read_csv(D + "tse-presidente-uf.csv").query("ano == 2022 and turno == 1").set_index("uf")
ufs = []
for r in res[res.uf != "BR"].itertuples():
    a = u22.loc[r.uf]
    ufs.append(dict(uf=r.uf, L22=round(a.pct_pt_validos, 1), F22=round(a.pct_antipt_validos, 1),
                    L26=None if pd.isna(r.lula) else float(r.lula), F26=None if pd.isna(r.flavio) else float(r.flavio), obs=r.obs))
out["ufs"] = ufs
x22 = u22[~u22.index.isin(["ZZ", "VT"])]
out["ufs22"] = dict(f=int((x22.votos_antipt > x22.votos_pt).sum()), total=len(x22))

html = open("apps/analise.template.html", encoding="utf-8").read().replace("__DATA__", json.dumps(out, ensure_ascii=False))
open("analise.html", "w", encoding="utf-8").write(html)
print("analise.html", len(html) // 1024, "KB")

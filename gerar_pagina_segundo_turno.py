"""Gera segundo-turno.html (aba do 2º turno de 25/10/2026: Lula × Flávio; dados embutidos) a partir de apps/segundo-turno.template.html.

Sem pesquisa de 2º turno posterior ao 1º turno (datasets/pesquisas-2turno-pos-1t-2026.csv vazio) a página é um simulador de cenários:
o usuário escolhe a parcela de Lula na disputa a dois e o Monte Carlo por UF (modelos/eleicoes-model.js, base: 2º turno de 2022) mostra o que isso implica.
Para atualizar: acrescente as pesquisas ao CSV (instituto, campo, base, lula, flavio; conferir na fonte) e rode python atualizar.py."""
import json

import nav
import pandas as pd

from pesquisas import SD_PISO_2T_PP, vies_eleicao

D = "datasets/"
par = json.load(open("modelos/parametros.json"))
nac = pd.read_csv(D + "tse-presidente-nacional.csv").set_index(["ano", "turno"])
br = pd.read_csv(D + "resultado-2026-turno1.csv").query("uf == 'BR'").iloc[0]
L, F = float(br.lula), float(br.flavio)
p = pd.read_csv(D + "pesquisas-2turno-pos-1t-2026.csv")
pesq = [dict(inst=r.instituto, campo=r.campo_fim, base=r.base, L=float(r.lula), F=float(r.flavio), s=round(100 * r.lula / (r.lula + r.flavio), 2),
             registro=None if pd.isna(r.registro) else r.registro, obs=None if pd.isna(r.obs) else r.obs) for r in p.itertuples()]
out = dict(
    par=par,
    r26=dict(L=L, F=F, O=round(100 - L - F, 2), vL=int(br.votos_lula), vF=int(br.votos_flavio), validos=round(br.votos_flavio / (F / 100)), s=round(100 * br.votos_lula / (br.votos_lula + br.votos_flavio), 2)),
    ancoras=dict(l1_2022=round(float(nac.loc[(2022, 1)].pct_pt_validos), 2), t1_2022=round(float(nac.loc[(2022, 1)].pct_pt_dois), 2), t2_2022=round(float(nac.loc[(2022, 2)].pct_pt_validos), 2),
                 pre_t1=round(100 * par["turno2"]["p_pesquisas"], 2), pre_t1_data=par["data_referencia"], demais_meio=round(L + (100 - L - F) / 2, 2), demais_todos=round(L + (100 - L - F), 2)),
    pesq=pesq, vies2=round(vies_eleicao(2)[0], 2), vies1=round(vies_eleicao(1)[0], 2), piso=SD_PISO_2T_PP,
)
html = nav.moldura(open("apps/segundo-turno.template.html", encoding="utf-8").read(), "segundo-turno.html").replace("__DATA__", json.dumps(out, ensure_ascii=False))
open("segundo-turno.html", "w", encoding="utf-8").write(html)
print("segundo-turno.html", len(html) // 1024, "KB")

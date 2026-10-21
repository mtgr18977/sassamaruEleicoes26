"""Gera previsao.html (aba "Previsão": só o 2º turno, com a previsão do modelo e o agregador de pesquisas) a partir de apps/previsao.template.html.

Entradas: modelos/parametros.json (modelo do 2º turno, de pesquisas.py + montecarlo.py), agregador.py (tendência das pesquisas pós-1º turno),
pesquisas.evolucao (chances ao longo do tempo) e datasets/pesquisas-2turno-pos-1t-2026.csv (as pesquisas do 2º turno, uma por linha).
Roda em atualizar.py depois de gerar_pagina_lula.py. A página inicial (index.html) fica com o histórico e o simulador."""
import json
from pathlib import Path

import pandas as pd

import agregador
import nav
from pesquisas import HOJE, P2022, SD_PISO_2T_PP, evolucao, vies_eleicao

D = "datasets/"
r1 = lambda x: None if pd.isna(x) else round(float(x), 2)

p = pd.read_csv(D + "pesquisas-2turno-pos-1t-2026.csv", parse_dates=["campo_fim", "divulgacao"])
p = p.sort_values(["campo_fim", "divulgacao"], ascending=False)
pesq2 = [dict(inst=r.instituto, fim=str(r.campo_fim.date()), div=str((r.divulgacao if pd.notna(r.divulgacao) else r.campo_fim).date()),
              n=int(r.amostra), l=r1(r.lula), f=r1(r.flavio), s=r1(100 * r.lula / (r.lula + r.flavio)),
              registro=None if pd.isna(r.registro) else r.registro) for r in p.itertuples()]

uf = pd.read_csv(D + "resultado-2026-turno1.csv").query("uf == 'BR'").iloc[0]
datas = sorted({*pd.date_range("2026-08-20", "2026-10-09", freq="7D").strftime("%Y-%m-%d"), "2026-10-02", "2026-10-09",
                *pd.date_range("2026-10-12", HOJE, freq="3D").strftime("%Y-%m-%d"), str(HOJE.date())})   # semanal até 9/10; depois a cada 3 dias e na data de referência
out = dict(modelo=json.load(open("modelos/parametros.json")),
           projmodel=dict(vies_medio={t: round(vies_eleicao(t)[0], 2) for t in (1, 2)}, vies_n_eleicoes={t: vies_eleicao(t)[1] for t in (1, 2)}),
           piso2t=SD_PISO_2T_PP, r1t_s=round(100 * float(uf.lula) / (float(uf.lula) + float(uf.flavio)), 2), p2022_2t=round(100 * P2022[2], 2),
           evolucao=evolucao(datas), agg=agregador.presidente(), pesq2=pesq2)
html = nav.moldura(Path("apps/previsao.template.html").read_text(encoding="utf-8"), "previsao.html").replace("__DATA__", json.dumps(out, ensure_ascii=False))
Path("previsao.html").write_text(html, encoding="utf-8")
print("previsao.html", len(html) // 1024, "KB")

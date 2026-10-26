"""O dashboard inteiro tem de estar na mesma rodada: cada página gerada reflete os CSVs e a data de referência de pesquisas.py.

Se alguém acrescentar uma pesquisa (ou mudar HOJE) e esquecer de rodar `python atualizar.py`, estes testes falham.
Rotina a cada rodada: linha nos dois CSVs de pesquisas, HOJE e HORIZONTE em pesquisas.py, `python atualizar.py`, conferir a home (Previsão), o Histórico e a aba 2º turno."""
import json
from pathlib import Path

import pandas as pd
import pytest

import pesquisas

RAIZ = Path(__file__).resolve().parent.parent


def dados(arq):
    s = (RAIZ / arq).read_text(encoding="utf-8")
    i = s.index("const D = ")
    return json.JSONDecoder().raw_decode(s[i + len("const D = "):])[0]


@pytest.fixture(scope="module")
def pg():
    return {a: dados(a) for a in ("previsao.html", "historico.html", "segundo-turno.html")}


def test_todas_as_paginas_tem_a_data_de_referencia_de_pesquisas_py(pg):
    hoje = str(pesquisas.HOJE.date())
    assert pg["historico.html"]["modelo"]["data_referencia"] == hoje
    assert pg["previsao.html"]["modelo"]["data_referencia"] == hoje
    assert pg["segundo-turno.html"]["par"]["data_referencia"] == hoje


def test_previsao_agregador_e_evolucao_vao_ate_a_data_de_referencia(pg):
    hoje, prev = str(pesquisas.HOJE.date()), pg["previsao.html"]
    assert prev["agg"]["hoje"] == hoje and prev["agg"]["turnos"]["2"]["datas"][-1] == hoje
    assert prev["evolucao"][-1]["data"] == hoje
    ult = prev["evolucao"][-1]
    assert abs(ult["s2"] - prev["modelo"]["turno2"]["p_pesquisas"]) < 5e-4          # o último ponto da evolução é o modelo de hoje


def test_nenhuma_pesquisa_depois_da_data_de_referencia():
    for csv, col in (("datasets/pesquisas-2026.csv", "divulgacao"), ("datasets/pesquisas-2turno-pos-1t-2026.csv", "divulgacao")):
        d = pd.read_csv(RAIZ / csv, parse_dates=["campo_fim", col])
        assert (d.campo_fim <= pesquisas.HOJE).all() and (d[col].dropna() <= pesquisas.HOJE).all(), csv


def test_toda_pesquisa_de_2o_turno_esta_nas_paginas(pg):
    p2 = pd.read_csv(RAIZ / "datasets/pesquisas-2turno-pos-1t-2026.csv")
    prev = pg["previsao.html"]
    assert len(prev["pesq2"]) == len(p2) == len(pg["segundo-turno.html"]["pesq"])
    campos = {(x["inst"], x["campo"]) for s in prev["agg"]["turnos"]["2"]["series"] for x in s["pontos"]}
    assert {(r.instituto, r.campo_fim) for r in p2.itertuples()} <= campos           # entra no agregador
    ult = p2[p2.campo_fim == p2.campo_fim.max()]                                       # várias pesquisas podem terminar no mesmo dia
    topo = [x for x in prev["pesq2"] if x["fim"] == p2.campo_fim.max()]
    assert prev["pesq2"][0]["fim"] == p2.campo_fim.max() and {x["inst"] for x in topo} == set(ult.instituto)


def test_toda_pesquisa_de_2026_esta_no_historico(pg):
    assert len(pg["historico.html"]["pesq26"]) == len(pd.read_csv(RAIZ / "datasets/pesquisas-2026.csv"))


def test_o_modelo_das_paginas_e_o_de_parametros_json(pg):
    par = json.load(open(RAIZ / "modelos/parametros.json", encoding="utf-8"))
    for a in ("previsao.html", "historico.html"):
        assert pg[a]["modelo"]["turno2"] == par["turno2"] and pg[a]["modelo"]["mc"]["turno2"]["base"] == "1º turno de 2026", a


def test_o_1o_turno_de_2026_do_tse_esta_no_historico(pg):
    nac = pd.read_csv(RAIZ / "datasets/tse-presidente-nacional.csv").query("ano == 2026 and turno == 1").iloc[0]
    x = [n for n in pg["historico.html"]["nac"] if n["ano"] == 2026 and n["turno"] == 1][0]
    assert abs(x["pt"] - nac.pct_pt_validos) < 0.01 and x["votos"] == int(nac.votos_pt)

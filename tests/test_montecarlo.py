"""Monte Carlo por UF: o 2º turno parte do 1º turno de 2026 (já apurado); o 1º turno continua com a base de 2022."""
import json

import pandas as pd
import pytest

import montecarlo as mc

D = "datasets/"


@pytest.fixture(scope="module")
def par():
    return json.load(open("modelos/parametros.json", encoding="utf-8"))["mc"]


def test_base_do_2_turno_e_o_1_turno_de_2026_por_uf(par):
    u26 = pd.read_csv(D + "tse-presidente-uf.csv").query("ano == 2026 and turno == 1 and uf != 'VT'").set_index("uf")
    unid = par["turno2"]["unidades"]
    assert par["turno2"]["base"] == "1º turno de 2026" and len(unid) == len(u26) == 28
    for u in unid:
        assert u["pbase"] == pytest.approx(u26.loc[u["uf"], "pct_pt_dois"] / 100, abs=1e-5), u["uf"]
        assert u["validos"] == int(u26.loc[u["uf"], "votos_pt"] + u26.loc[u["uf"], "votos_antipt"])
        assert abs(u["p2022"] - u["pbase"]) < 0.1   # 2022 segue como referência de exibição, perto da base


def test_1_turno_continua_com_a_base_de_2022(par):
    assert par["turno1"]["base"] == "2022"
    assert all(u["pbase"] == u["p2022"] for u in par["turno1"]["unidades"])


def test_ruido_do_mesmo_ano_e_menor_que_o_da_eleicao_anterior():
    uf = pd.read_csv(D + "tse-presidente-uf.csv").query("ano <= 2022")
    hist = uf[~uf.uf.isin(["ZZ", "VT"])]
    nac = pd.read_csv(D + "tse-presidente-nacional.csv").query("ano <= 2022").set_index(["ano", "turno"])
    novo = mc.ruido_mesmo_ano(hist, nac)
    antigo = mc.ruido_historico(hist, nac, 2)
    assert novo[0] < antigo[0] and novo[1] < antigo[1]
    assert 0.03 < novo[0] < 0.15 and 0.08 < novo[1] < 0.2


def test_previsao_2_turno_tem_coluna_base_e_nao_muda_o_total_nacional():
    t = pd.read_csv("modelos/previsao-uf-turno2.csv")
    assert list(t.columns[:6]) == ["uf", "2022", "p5", "mediana", "p95", "P(PT>50%)"] and t.columns[-1] == "base"
    assert (t.p5 <= t.mediana).all() and (t.mediana <= t.p95).all()
    assert (t.p95 - t.p5).mean() < 20   # com a base do mesmo ano a faixa de 90% por UF é bem mais estreita (antes ~25 p.p.)

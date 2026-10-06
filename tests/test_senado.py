import pandas as pd
import pytest

import senado


@pytest.fixture(scope="module")
def r():
    return senado.construir()


def test_54_eleitos_2_por_uf_e_listas_fecham(r):
    assert len(r["ufs"]) == 27 and all(len(u["eleitos"]) == 2 for u in r["ufs"])
    for col in ("e18", "atual", "real"):
        assert sum(l[col] for l in r["listas"]) == 54
        assert sum(b[col] for b in r["blocos"].values()) == 54


def test_senado_de_2027_tem_81_cadeiras(r):
    assert sum(b["fica"] + b["eleitos"] for b in r["nb"].values()) == 81
    assert sum(r["hoje"].values()) == 81


def test_margem_usa_votos_validos_e_exclui_sub_judice(r):
    ac = next(u for u in r["ufs"] if u["uf"] == "AC")
    assert ac["vice"]["nome"] != "Gladson Camelí" and ac["sub_judice"]
    assert all(u["margem"] > 0 for u in r["ufs"])


def test_linhagem_dos_partidos():
    assert senado.lin("DEM") == "UNIÃO" and senado.lin("PR") == "PL" and senado.lin("PTB") == "PRD" and senado.lin("PHS") == "PODE"


def test_titulo_dos_nomes():
    assert senado.titulo("SAMANDA DE LULA") == "Samanda de Lula"


def test_resultado_confere_com_a_imprensa_nos_extremos():
    b = pd.read_csv("datasets/tse-senado-2026.csv")
    e = b[b.situacao == "ELEITO"]
    assert (e.partido == "PL").sum() == 19 and e.groupby("uf").size().eq(2).all()


# ---------------------------------------------------------------- modelo (senado_modelo.py)
import numpy as np

import senado_modelo as sm


@pytest.fixture(scope="module")
def m():
    return sm.construir()


def test_ajuste_recupera_parametros_conhecidos():
    rng = np.random.default_rng(0)
    x = rng.uniform(0.25, 0.75, 4000)
    e = pd.DataFrame(dict(x=x, n=2, D=rng.binomial(2, sm.probabilidade(-0.4, 2.0, x))))
    a, b = sm.ajustar(e)
    assert abs(a + 0.4) < 0.15 and abs(b - 2.0) < 0.3


def test_alfa_calibrado_acerta_o_total():
    e = sm.painel()[2022]
    a = sm.alfa_para_total(e, 1.5, e.D.sum())
    assert abs((e.n * sm.probabilidade(a, 1.5, e.x)).sum() - e.D.sum()) < 1e-6


def test_painel_fecha_vagas_e_direita_de_2026(m):
    P = sm.painel()
    assert [int(P[y].n.sum()) for y in sm.ANOS] == [27, 54, 27, 54] and P[2026].D.sum() == 32
    assert sum(u["D"] for u in m["ufs"]) == 32 and abs(sum(u["esperado"] for u in m["ufs"]) - 32) < 0.05


def test_voto_no_senado_se_nacionalizou(m):
    beta = {a["ano"]: a["beta"] for a in m["ajustes"]}
    assert beta[2014] < beta[2018] < beta[2022]


def test_parametros_anteriores_erram_o_total_e_o_alfa_calibrado_melhora(m):
    for b in m["backtest"]:
        assert b["trocadas_cal"] <= b["trocadas"] and b["trocadas_cal"] < b["vagas"] / 4
    assert m["backtest"][-1]["esperado"] > m["backtest"][-1]["real"] + 5          # 2026: o modelo com os parâmetros de 2022 passa de 40

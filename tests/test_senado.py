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

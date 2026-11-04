"""Colégio Eleitoral: delegados por UF, vencedor leva tudo e distritos desenhados (zonas agrupadas) sobre o resultado oficial do 2º turno."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import colegio_eleitoral as ce

RAIZ = Path(__file__).resolve().parent.parent
D = json.load(open(RAIZ / "modelos/colegio-eleitoral.json", encoding="utf-8"))
UF = pd.read_csv(RAIZ / "datasets/tse-presidente-2turno-uf.csv").set_index("uf")


@pytest.fixture(scope="module")
def z():
    return ce.carregar()


def test_cadeiras_e_delegados_fecham():
    assert sum(ce.CADEIRAS.values()) == 513 and len(ce.CADEIRAS) == 27
    assert D["cadeiras"] == 513 and D["total_delegados"] == 513 + 3 * 27 == 594 and D["maioria"] == 298
    assert sum(u["delegados"] for u in D["por_uf"]) == 594 and all(u["delegados"] == u["cadeiras"] + 3 for u in D["por_uf"])


def test_vencedor_leva_tudo_e_proporcional_batem_com_o_tse_por_uf():
    lula = sum(ce.CADEIRAS[u] + 3 for u in ce.CADEIRAS if UF.votos_lula[u] > UF.votos_flavio[u])
    prop = sum((ce.CADEIRAS[u] + 3) * UF.votos_lula[u] / (UF.votos_lula[u] + UF.votos_flavio[u]) for u in ce.CADEIRAS)
    assert D["regras"]["vencedor_leva"] == lula == 276 and D["regras"]["proporcional_uf"] == round(prop, 1)
    assert D["ufs_venceu_lula"] + D["ufs_venceu_flavio"] == 27
    for u in D["por_uf"]:
        assert u["vence"] == ("Lula" if UF.votos_lula[u["uf"]] > UF.votos_flavio[u["uf"]] else "Flávio")
        assert abs(u["lula_pct"] - UF.lula_pct_validos[u["uf"]]) < 0.01


def test_voto_popular_das_ufs_mais_exterior_fecha_com_o_nacional():
    nac = UF.loc["BR"]
    assert D["popular"]["lula"] + D["popular"]["flavio"] + D["exterior_ignorado"] == nac.votos_lula + nac.votos_flavio
    assert D["popular"]["lula_pct"] > 50 and D["regras"]["vencedor_leva"] < D["maioria"]


def test_toda_zona_cai_em_um_distrito_e_cada_uf_tem_tantos_distritos_quanto_cadeiras(z):
    d = ce.distritos(z, np.random.default_rng(0), 0.0)
    z = z.assign(d=d)
    for u, n in ce.CADEIRAS.items():
        assert sorted(z[z.uf == u].d.unique()) == list(range(n)), u


def test_distritos_tem_votos_parecidos_e_o_total_de_votos_se_preserva(z):
    tot = pd.read_csv(RAIZ / "datasets/tse-presidente-zona-2026.csv").query("uf != 'ZZ'")
    assert abs(z.peso.sum() - (tot.lula_t2 + tot.flavio_t2).sum()) < 1
    z = z.assign(d=ce.distritos(z, np.random.default_rng(0), 0.0))
    t = z.groupby(["uf", "d"]).peso.sum()
    desvio = (t / t.groupby("uf").transform("mean") - 1).abs()
    assert desvio.groupby("uf").max().max() < 0.6 and desvio.mean() < 0.1


def test_desenho_neutro_e_deterministico_e_o_json_e_o_desenho_base(z):
    a = ce.placar(z, ce.distritos(z, np.random.default_rng(1), 0.0))
    b = ce.placar(z, ce.distritos(z, np.random.default_rng(2), 0.0))
    assert a["lula_distritos_puro"] == b["lula_distritos_puro"] == D["regras"]["distritos_puro"]
    assert a["lula_distritos_bonus"] == D["regras"]["distritos_bonus"]
    assert a["lula_distritos_bonus"] == a["lula_distritos_puro"] + 3 * sum(a["uf_lula"].values())


def test_faixa_dos_sorteios_e_a_conclusao_da_pagina():
    for k, maioria in (("distritos_bonus", D["maioria"]), ("distritos_puro", D["maioria_puro"])):
        f = D["faixa"][k]
        assert f["min"] <= f["p5"] <= f["mediana"] <= f["p95"] <= f["max"] and sum(h["n"] for h in f["hist"]) == D["sorteios"]
        assert f["max"] < maioria and f["prob_lula"] == 0.0   # nenhum sorteio dá a maioria a Lula
    assert D["regras"]["proporcional_uf"] > D["maioria"]


def test_distritos_de_cada_uf_somam_as_cadeiras_e_a_faixa_contem_o_desenho_base():
    for u in D["por_uf"]:
        assert u["dist_lula"] + u["dist_flavio"] == u["cadeiras"]
        assert u["dist_lula_min"] <= u["dist_lula_max"]
    assert sum(u["dist_lula"] for u in D["por_uf"]) == D["regras"]["distritos_puro"]


def test_pagina_gerada_tem_os_dados_e_esta_no_menu():
    s = (RAIZ / "colegio-eleitoral.html").read_text(encoding="utf-8")
    assert '"vencedor_leva":276' in s and "__DATA__" not in s and 'aria-current="page">Colégio Eleitoral' in s
    assert (RAIZ / "documentacao.html").read_text(encoding="utf-8").count("colegio-eleitoral.html") >= 1

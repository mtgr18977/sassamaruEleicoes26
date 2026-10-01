import json

import numpy as np
import pandas as pd

import projecao
from pesquisas import estimar, preparar


def _unidades():
    return pd.DataFrame(dict(uf=list("ABCD"), regiao=["N", "N", "S", "S"], validos=[1e6, 2e6, 3e6, 4e6],
                             s0=[.6, .55, .45, .4], q0=[.9, .88, .92, .9]))


def test_partes_somam_100_e_total_nacional_bate_com_o_sorteado():
    u = _unidades()
    L, F, O = projecao.simular(u, .52, .02, .88, .02, (.1, .1), (.1, .1))
    assert np.allclose(L + F + O, 1)
    w = (u.validos / u.validos.sum()).to_numpy()
    assert abs(np.median(L @ w) - .52 * .88) < .01        # Lula nacional ≈ s·q


def test_regressao_estimativas_das_pesquisas_nas_faixas_esperadas():
    # trava bugs de código; se as pesquisas do CSV mudarem muito, atualize as faixas
    d = preparar()
    assert .44 < estimar(d, "p1")[0] < .46 and .48 < estimar(d, "p2")[0] < .51


def test_projecao_congelada_de_1_10_nao_foi_sobrescrita():
    j = json.load(open("modelos/projecao-1turno.json"))
    assert j["data"] == "2026-10-01" and abs(j["pesquisas"]["L"][1] - 45.2) < 0.05

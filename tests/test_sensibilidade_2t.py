import json

import sensibilidade_2t as sens


def test_base_bate_com_o_modelo_e_os_cenarios_se_comportam():
    t, w = sens.montar()
    base = t.iloc[0]
    par = json.load(open("modelos/parametros.json"))["turno2"]
    assert abs(base.s2 - 100 * par["p_pesquisas"]) < 0.05                      # a base é o modelo atual
    corr = t.set_index("cenario")
    assert corr.loc["Cada instituto − erro inteiro do 1º turno"].s2 < corr.loc["Cada instituto − metade do erro do 1º turno"].s2 < base.s2
    assert (t.lo < t.s2).all() and (t.s2 < t.hi).all() and t.chance_lula.between(0, 100).all()
    assert abs(w.mean() - 1) < 1e-9 and w["Gerp"] > w["Quaest"]                 # quem errou menos pesa mais

import json

import abstencao_2t as ab


def test_composicao_e_efeitos():
    x = ab.base_2022()
    c = ab.composicao(x)
    assert sum(g["ufs"] for g in c) == 27 and abs(sum(g["aptos_pct"] for g in c) - 100) < 0.2 and abs(sum(g["lula_pct"] for g in c) - 100) < 0.2
    assert len(ab.GOV2[2026]) == 7 and (x.gov26.sum() == 7)
    assert abs(ab.efeito(x, 3, "proporcional")) < 0.05                       # ausentes dos dois lados na proporção local: quase nada
    assert abs(ab.efeito(x, 1) - 0.57) < 0.03 and ab.efeito(x, 2) > ab.efeito(x, 1) > 0   # só do lado do Flávio: cresce com a abstenção
    assert abs(ab.efeito(x, ab.delta_para(x, 2.0)) - 2.0) < 1e-3              # a busca do ponto de quebra fecha


def test_historico_e_json():
    h = ab.historico(ab._uf())
    assert h["n"] == 54 and abs(h["efeito_gov2"]) < 3 and h["efeito_ic"] > 0 and {a["ano"] for a in h["por_ano"]} == {2018, 2022}
    j = json.load(open("modelos/abstencao-2t.json", encoding="utf-8"))
    assert j["ufs_2026_com_gov2"] == sorted(ab.GOV2[2026]) and len(j["cenarios"]) == 5 and len(j["quebra"]) == 2

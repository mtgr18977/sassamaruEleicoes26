import json

import pandas as pd


def test_resultado_do_2o_turno_tem_as_27_ufs_e_o_nacional():
    r = pd.read_csv("datasets/resultado-2026-turno2.csv").set_index("uf")
    assert "BR" in r.index and len(r) == 28 and r.lula_pct.between(20, 80).all()
    assert abs(r.loc["BR", "lula_pct"] - 100 * 64241786 / (64241786 + 59818887)) < 0.05      # Wikipedia/TSE: 51,78%


def test_avaliacao_bate_com_as_tabelas():
    a = json.load(open("modelos/avaliacao-2turno.json", encoding="utf-8"))
    assert abs(a["nacional"]["erro_modelo"] - (a["nacional"]["modelo"] - a["nacional"]["real"])) < 0.01
    assert a["uf_resumo"]["n"] == 27 == len(a["tabela_uf"]) and len(a["tabela_institutos"]) >= 14
    assert abs(sum(r["erro"] for r in a["tabela_uf"]) / 27 - a["uf_resumo"]["vies"]) < 0.02

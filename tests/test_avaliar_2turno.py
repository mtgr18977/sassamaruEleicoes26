import json

import pandas as pd


def test_resultado_do_2o_turno_tem_as_27_ufs_e_o_nacional():
    r = pd.read_csv("datasets/resultado-2026-turno2.csv").set_index("uf")
    assert "BR" in r.index and len(r) == 29 and r.lula_pct.between(20, 80).all()              # Brasil + 27 UFs + exterior (ZZ)
    assert abs(r.loc["BR", "lula_pct"] - 100 * 64256232 / (64256232 + 59826041)) < 0.001     # TSE oficial, 100% das seções: 51,79%
    t = pd.read_csv("datasets/tse-presidente-2turno-uf.csv").set_index("uf")
    assert t.drop(index="BR").votos_lula.sum() == t.loc["BR", "votos_lula"] and t.drop(index="BR").votos_flavio.sum() == t.loc["BR", "votos_flavio"]   # as UFs somam o nacional
    assert 0 <= t.loc["BR", "eleitorado"] - (t.loc["BR", "comparecimento"] + t.loc["BR", "abstencao"]) < 1000 and t.loc["BR", "secoes_apuradas_pct"] == 100   # sobram 423 eleitores de seções não instaladas


def test_avaliacao_bate_com_as_tabelas():
    a = json.load(open("modelos/avaliacao-2turno.json", encoding="utf-8"))
    assert abs(a["nacional"]["erro_modelo"] - (a["nacional"]["modelo"] - a["nacional"]["real"])) < 0.01
    assert a["uf_resumo"]["n"] == 27 == len(a["tabela_uf"]) and a["exterior"]["erro"] < 0 and len(a["tabela_institutos"]) >= 14
    assert abs(sum(r["erro"] for r in a["tabela_uf"]) / 27 - a["uf_resumo"]["vies"]) < 0.02


def test_a_previsao_avaliada_e_a_de_25_10_e_nao_mudou():
    """O 2º turno já aconteceu: modelos/parametros.json guarda a previsão de 25/10 (49,03%; chance de Lula 34,9%). Se este teste falhar, alguém regenerou o modelo com outros dados:
    a página Resultado compara o resultado com a previsão que foi publicada, então não regenere pesquisas.py/montecarlo.py depois da eleição (ou atualize o texto da página)."""
    p = json.load(open("modelos/parametros.json", encoding="utf-8"))["turno2"]
    assert abs(p["p_pesquisas"] - 0.4903) < 1e-4 and p["n_pesquisas"] == 37
    a = json.load(open("modelos/avaliacao-2turno.json", encoding="utf-8"))
    assert a["nacional"]["modelo"] == 49.03 and a["nacional"]["chance_lula_modelo"] == 34.9


def test_a_home_e_o_resultado_e_a_previsao_tem_a_faixa():
    r = open("index.html", encoding="utf-8").read()
    assert "Resultado do 2º turno" in r and "__DATA__" not in r and '"tabela_uf"' in r and "oficial do TSE" in r
    home = open("previsao.html", encoding="utf-8").read()
    assert 'id="faixaResultado"' in home and '"resultado": {' in home


def test_incongruencias_medidas_batem_com_as_tabelas():
    a = json.load(open("modelos/avaliacao-2turno.json", encoding="utf-8"))
    assert len(a["efeitos_instituto"]) == 16 and abs(sum(e["pp"] for e in a["efeitos_instituto"])) < 0.5     # os efeitos de instituto somam ~zero
    r = a["arredondamento_resumo"]
    assert r["n"] == len(a["arredondamento"]) == 12 and r["max_abs"] <= 0.6 and abs(r["media"]) < 0.2             # totais × válidos: diferença de arredondamento, sem sinal
    assert a["sem_instituto"]["max_mudanca"] < 0.2                                                                   # nenhum instituto, sozinho, move o nível mais que 0,2 p.p.
    home = open("index.html", encoding="utf-8").read()
    assert "Como o modelo funciona, passo a passo" in home and "O que eu faria diferente" in home


def test_conta_de_votos_entre_os_turnos_fecha():
    a = json.load(open("modelos/avaliacao-2turno.json", encoding="utf-8"))
    c = a["contabilidade"]
    assert abs(c["outros_1t"] + c["queda_branco_nulo"] + c["mais_comparecimento"] - c["ganho_lula"] - c["ganho_flavio"]) < 10000     # identidade: sobra de poucos milhares de votos
    assert c["ganho_lula"] == c["lula_2t"] - c["lula_1t"] and c["ganho_flavio"] == c["flavio_2t"] - c["flavio_1t"]
    h = {r["ano"]: r for r in a["historico_conta"]}
    assert set(h) == {2002, 2006, 2010, 2014, 2018, 2022, 2026} and h[2026]["ganho_anti"] < h[2022]["ganho_anti"]
    assert a["teste_comparecimento"]["ufs_com_swing_positivo"] == 27 and len(a["uf_turnos"]) == 27

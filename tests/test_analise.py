import pandas as pd


def test_resultado_preliminar_tem_fonte_e_soma_menor_que_100():
    r = pd.read_csv("datasets/resultado-2026-turno1.csv")
    assert r.fonte.notna().all() and r.obs.notna().all()
    br = r[r.uf == "BR"].iloc[0]
    assert br.lula + br.flavio < 100
    assert abs(100 * br.votos_lula / (br.votos_lula + br.votos_flavio) - 48.99) < 0.01
    # % divulgados coerentes com os votos (mesma base de válidos)
    assert abs(br.votos_lula / br.lula - br.votos_flavio / br.flavio) / (br.votos_flavio / br.flavio) < 0.001

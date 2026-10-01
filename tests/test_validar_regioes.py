from validar_regioes import comparar


def test_distribuicao_regional_do_modelo_dentro_de_5pp_da_datafolha():
    r = comparar()
    assert len(r) == 8 and all(abs(x["dif"]) < 5 for x in r)

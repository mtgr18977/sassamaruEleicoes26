from validar_regioes import comparar, estrutura


def test_distribuicao_regional_do_1_turno_dentro_de_5pp_da_datafolha():
    r = [x for x in comparar() if x["turno"] == 1]
    assert len(r) == 4 and all(abs(x["dif"]) < 5 for x in r)


def test_estrutura_regional_dos_dois_turnos_dentro_de_5pp_da_datafolha_descontado_o_nivel():
    r = estrutura()
    assert len(r) == 8 and all(abs(x["dif_estrutura"]) < 5 for x in r)

import numpy as np

import rs_modelo as rm
from rs_dados import blocos_por_unidade, carregar


def test_base_do_rs_cobre_os_497_municipios_e_os_blocos_somam_100():
    m = carregar()
    assert m.drop_duplicates("cod_municipio").shape[0] == 497 and m.unidade.notna().all()
    u = blocos_por_unidade(m)
    assert np.allclose(u[["E", "C", "D"]].sum(axis=1), 1) and u.unidade_nome.nunique() == 8
    est = m[(m.ano == 2022) & (m.turno == 1)].groupby("bloco").votos.sum()
    assert abs(100 * est["D"] / est.sum() - 44.4) < 0.2           # Onyx + PP + PSC + Novo


def test_pesquisas_do_rs_somam_100_e_o_modelo_fecha():
    d = rm.preparar()
    tot = d[["zucco", "brizola", "souza", "maranata", "outros", "bn", "indecisos"]].sum(axis=1)
    assert ((tot > 99.8) & (tot < 100.2)).all()                    # transcrição das matérias consistente
    par = rm.parametros(d)
    sh = np.exp([0, *par["mu"]]); sh = 100 * sh / sh.sum() * (1 - par["rbar"])
    assert 41 < sh[0] < 46 and 34 < sh[1] < 38.5                   # faixas de regressão; atualizar se as pesquisas mudarem muito
    r = rm.chances(par, n=20000)
    assert abs(sum(r["eleito"]) - 1) < 1e-9 and 0.8 < r["eleito"][0] < 0.95


def test_ruido_regional_medido_e_plausivel_e_a_calibracao_bate_com_os_totais():
    sg = rm.ruido_unidade()
    assert 0.2 < sg < 0.4
    par = rm.parametros(rm.preparar()); u = rm.unidades()
    reg = rm.regioes(par, u, sg, n=3000)
    w = (u.validos / u.validos.sum()).to_numpy()
    sh = np.exp([0, *par["mu"]]); sh = sh / sh.sum() * (1 - par["rbar"])
    assert abs((reg.zucco.to_numpy() / 100) @ w - sh[0]) < 0.01     # média ponderada das regiões ≈ total estadual

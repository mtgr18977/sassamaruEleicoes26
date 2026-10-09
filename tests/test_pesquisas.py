import pandas as pd
from pesquisas import estimar


def test_house_effect_recuperado_e_nivel_e_media():
    # dois institutos, tendência nula, A sempre 0,50 e B sempre 0,54
    datas = pd.date_range("2026-09-01", periods=6, freq="5D")
    d = pd.DataFrame([dict(instituto=i, data=t, n=2000, p=p) for t in datas for i, p in (("A", .50), ("B", .54))])
    p, sd, h, _ = estimar(d, "p", hoje=pd.Timestamp("2026-09-30"))
    assert abs(p - 0.52) < 0.005 and h["B"] > 0 > h["A"] and sd > 0


def test_incerteza_cresce_com_o_prazo_ate_a_eleicao():
    datas = pd.date_range("2026-08-01", periods=12, freq="5D")
    d = pd.DataFrame([dict(instituto=i, data=t, n=1500, p=.50 + .002 * k) for k, t in enumerate(datas) for i in "AB"])
    hoje = pd.Timestamp("2026-09-30")
    assert estimar(d, "p", hoje=hoje, h_dias=60)[1] > estimar(d, "p", hoje=hoje, h_dias=0)[1]


def test_evolucao_so_usa_pesquisas_ate_a_data_e_a_ultima_bate_com_o_modelo_atual():
    from pesquisas import evolucao, preparar, vies_rmse
    d = preparar()
    assert evolucao(["2026-06-01"]) == []                      # pesquisas insuficientes: pula a data
    atual = evolucao(["2026-10-02"])[0]
    s, _, _, _ = estimar(d, "p1s", hoje=pd.Timestamp("2026-10-02"), sd_vies=vies_rmse(1)[0], h_dias=2)
    assert abs(atual["s"] - s) < 1e-4
    assert evolucao(["2026-09-24"])[0]["n2"] < atual["n2"]     # menos pesquisas de 2º turno na data anterior


def test_vies_por_eleicao_nao_conta_2022_tres_vezes():
    from pesquisas import vies_eleicao
    m1, n1, _ = vies_eleicao(1)
    m2, n2, _ = vies_eleicao(2)
    assert (n1, n2) == (3, 2) and abs(m1 - 2.25) < 0.1 and abs(m2 - 0.83) < 0.1   # por pesquisa seriam 2,75 e 1,17


def test_piso_de_incerteza_em_pp_vira_logit_e_so_age_quando_maior():
    datas = pd.date_range("2026-08-01", periods=12, freq="5D")
    d = pd.DataFrame([dict(instituto=i, data=t, n=5000, p=.50) for t in datas for i in "AB"])
    hoje = pd.Timestamp("2026-09-30")
    p, sd0, _, _ = estimar(d, "p", hoje=hoje, sd_vies=0.0)
    _, sd1, _, _ = estimar(d, "p", hoje=hoje, sd_vies=0.0, piso_pp=2.5)
    assert abs(sd1 - 0.025 / (p * (1 - p))) < 1e-9 and sd1 > sd0          # 2,5 p.p. em p=0,5 = 0,10 em logit
    assert estimar(d, "p", hoje=hoje, sd_vies=0.05, piso_pp=0.1)[1] > 0.1  # piso menor que a incerteza: não muda

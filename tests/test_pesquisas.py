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

import numpy as np
import pandas as pd

import agregador as ag


def _sintetico(vies=0.03):
    datas = pd.date_range("2026-08-01", periods=40, freq="D")
    d = pd.DataFrame(dict(data=datas, instituto=["A", "B"] * 20, n=2000, y=0.40))
    d.loc[d.instituto == "B", "y"] += vies
    return d, list(datas)


def test_tendencia_constante_recupera_o_nivel_e_o_vies_dos_institutos():
    d, g = _sintetico()
    r = ag.tendencia(d, g, ajustar=True)
    assert np.allclose(r["m"][5:-5], 41.5, atol=0.15)                         # nível = média dos institutos
    assert abs((r["vies"]["B"] - r["vies"]["A"]) - 3) < 0.4                   # diferença de 3 p.p. (encolhida, mas perto)
    assert abs(sum(r["vies"].values())) < 1e-6                                # centrado em zero
    bruta = ag.tendencia(d, g, ajustar=False)
    assert all(v == 0 for v in bruta["vies"].values())


def test_faixa_contem_a_media_e_cresce_sem_pesquisa_recente():
    d, g = _sintetico()
    g = g + list(pd.date_range(g[-1] + pd.Timedelta(days=1), periods=21, freq="D"))   # 3 semanas sem pesquisa
    r = ag.tendencia(d, g)
    assert all(lo < m < hi for lo, m, hi in zip(r["lo"], r["m"], r["hi"]))
    assert (r["hi"][-1] - r["lo"][-1]) > (r["hi"][20] - r["lo"][20])


def test_pacotes_do_site_tem_series_nos_dois_turnos_e_valores_plausiveis():
    for p in (ag.presidente(), ag.rs()):
        assert len(p["datas"]) > 30 and set(p["turnos"]) == {"1", "2"}
        for t in p["turnos"].values():
            for s in t["series"]:
                assert len(s["aj"]["m"]) == len(p["datas"]) and 0 < s["hoje"] < 100 and s["pontos"]
    ult = ag.presidente()["turnos"]["2"]["series"]
    assert abs(ult[0]["hoje"] + ult[1]["hoje"] - 100) < 0.05                   # 2º turno fecha em 100

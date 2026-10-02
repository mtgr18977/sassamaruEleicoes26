import pandas as pd

import agregador

HOJE = pd.Timestamp("2026-10-02")


def test_presidente_intervalo_contem_tendencia():
    r = agregador.presidente(HOJE)
    assert set(r["series"]) == {"Lula (PT)", "Flávio Bolsonaro (PL)", "Demais candidatos"}
    for s in r["series"].values():
        assert all(x["lo"] < x["m"] < x["hi"] for x in s)
        assert s[-1]["data"] == "2026-10-02"
    ult = [r["series"][k][-1]["m"] for k in r["series"]]
    assert abs(sum(ult) - 100) < 1.5          # as três fatias somam ~100%


def test_rs_fatias_somam_100():
    r = agregador.rs(HOJE)
    assert abs(sum(s[-1]["m"] for s in r["series"].values()) - 100) < 1.5
    assert all(x["lo"] < x["hi"] for s in r["series"].values() for x in s)

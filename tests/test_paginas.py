import re
from pathlib import Path

import nav

RAIZ = Path(__file__).resolve().parent.parent


def _abas(arq):
    s = (RAIZ / arq).read_text(encoding="utf-8")
    return re.search(r'<nav class="tabs"[^>]*>(.*?)</nav>', s, re.S).group(1)


def test_todas_as_paginas_tem_o_mesmo_menu_com_a_aba_atual_marcada():
    for href, _ in nav.ABAS:
        assert _abas(href) == nav.html(href), href


def test_segundo_turno_e_a_primeira_aba():
    assert nav.ABAS[0][0] == "segundo-turno.html"


def test_bancada_do_rs_fecha_as_cadeiras_e_o_governador_fecha_100():
    import pandas as pd
    b = pd.read_csv(RAIZ / "datasets/resultado-2026-rs-bancada.csv").groupby("cargo").cadeiras.sum()
    assert b["DF"] == 31 and b["DE"] == 55
    g = pd.read_csv(RAIZ / "datasets/resultado-2026-rs-governador.csv").query("cargo == 'GOVERNADOR'")
    assert abs(g.pct.sum() - 100) < 0.01
    assert abs(g.votos.dropna().sum() / 6056120 * 100 - (g.pct.iloc[:3].sum())) < 0.05

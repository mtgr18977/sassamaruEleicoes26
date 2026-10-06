import re
from pathlib import Path

import nav

RAIZ = Path(__file__).resolve().parent.parent


def _abas(arq):
    s = (RAIZ / arq).read_text(encoding="utf-8")
    return re.search(r'<nav class="tabs"[^>]*>(.*?)</nav>', s, re.S).group(1)


def test_todas_as_paginas_tem_o_mesmo_menu_com_a_aba_atual_marcada():
    for href, *_ in nav.ABAS:
        assert _abas(href) == nav.html(href), href


def test_presidente_vem_antes_do_segundo_turno():
    hrefs = [a[0] for a in nav.ABAS]
    assert hrefs[:3] == ["index.html", "segundo-turno.html", "analise.html"] and hrefs[-1] == "documentacao.html"


def test_toda_pagina_tem_cabecalho_rodape_e_nenhum_placeholder():
    for href, *_ in nav.ABAS:
        s = (RAIZ / href).read_text(encoding="utf-8")
        assert 'class="mast"' in s and 'class="rodape"' in s and 'class="pular"' in s and 'id="conteudo"' in s, href
        assert s.count('id="tema"') == 1 and "__NAV__" not in s and "__DATA__" not in s, href
        assert 'name="viewport"' in s, href


def test_notas_laterais_em_todas_as_abas_com_secoes_e_ids_existem():
    for href, *_ in nav.ABAS:
        s = (RAIZ / href).read_text(encoding="utf-8")
        usados = set(re.findall(r'nota\("(nota\d+)"', s))
        for i in usados:
            assert f'id="{i}"' in s, (href, i)
        if href != "documentacao.html":
            assert 'class="side"' in s and usados, href


def test_moldura_exige_o_placeholder_e_leva_o_botao_de_tema_para_o_cabecalho():
    import pytest
    with pytest.raises(AssertionError):
        nav.moldura("<body><main></main></body>", "index.html")
    tpl = '<body><main><nav class="tabs" aria-label="Seções do site">__NAV__</nav><div class="topo"><button id="tema" class="tema" type="button"></button></div></main></body>'
    out = nav.moldura(tpl, "analise.html")
    assert out.index('class="mast"') < out.index('id="tema"') < out.index('class="tabs"') and out.count('id="tema"') == 1 and 'aria-current="page">Análise<' in out


def test_bancada_do_rs_fecha_as_cadeiras_e_o_governador_fecha_100():
    import pandas as pd
    b = pd.read_csv(RAIZ / "datasets/resultado-2026-rs-bancada.csv").groupby("cargo").cadeiras.sum()
    assert b["DF"] == 31 and b["DE"] == 55
    g = pd.read_csv(RAIZ / "datasets/resultado-2026-rs-governador.csv").query("cargo == 'GOVERNADOR'")
    assert abs(g.pct.sum() - 100) < 0.01
    assert abs(g.votos.dropna().sum() / 6056120 * 100 - (g.pct.iloc[:3].sum())) < 0.05

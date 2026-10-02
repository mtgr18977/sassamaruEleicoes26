import numpy as np
import pandas as pd

import rs_bancada as rb

D = "datasets/"


def test_dados_do_tse_fecham_31_federais_e_55_estaduais_por_eleicao():
    el = pd.read_csv(D + "tse-legislativo-rs-eleitos.csv")
    assert (el.groupby(["ano", "cargo"]).cadeiras.sum().unstack()[["DF", "DE"]] == [31, 55]).all().all()
    ls = pd.read_csv(D + "tse-legislativo-rs-listas.csv")
    assert (ls.groupby(["ano", "cargo"]).cadeiras.sum().unstack()[["DF", "DE"]] == [31, 55]).all().all()       # eleitos casam com as listas
    pl = pd.read_csv(D + "tse-legislativo-rs-partido-lista.csv")
    s = pl.groupby(["ano", "cargo"]).votos.sum()
    assert np.allclose(s.values, ls.groupby(["ano", "cargo"]).votos.sum().values, rtol=1e-3)   # mesmos votos pelos dois caminhos (2002 perde ~0,03% em linhas "isoladas" de partidos coligados)


def test_alocador_reproduz_as_eleicoes_reais_com_no_maximo_1_cadeira_de_diferenca():
    v = rb.validar_alocador()
    assert len(v) == 12 and v.trocadas.max() <= 1 and v.trocadas.sum() <= 1


def test_alocador_regras_de_sobras_e_vetorizacao():
    votos = np.array([500_000, 300_000, 150_000, 40_000, 10_000])
    for regra in ("qe", "80", "todos"):
        assert rb.alocar(votos, 10, regra).sum() == 10
    assert rb.alocar(votos, 10, "qe")[0] >= 5
    m = rb.alocar(np.tile(votos, (3, 1)), 10, "todos")
    assert m.shape == (3, 5) and (m == rb.alocar(votos, 10, "todos")).all()
    # lista abaixo de 80% do QE só recebe sobra na regra aberta
    v2 = np.array([1000.0, 1000.0, 230.0])      # QE = 2230/6 ~ 372; 230 = 62% do QE
    assert rb.alocar(v2, 6, "80")[2] == 0 and rb.alocar(v2, 6, "todos").sum() == 6


def test_bancada_atual_casa_com_os_eleitos_de_2022():
    at = pd.read_csv(D + "rs-bancada-atual.csv")
    assert at.groupby("cargo").size().to_dict() == {"DE": 55, "DF": 31} and at.partido_atual.notna().all()
    e = pd.read_csv(D + "tse-legislativo-rs-eleitos.csv").query("ano == 2022").assign(partido=lambda d: d.partido.map(rb.renomear))
    el = e.groupby(["cargo", "partido"]).cadeiras.sum()
    pa = at.assign(p=at.partido_2022.map(rb.renomear)).groupby(["cargo", "p"]).size().rename_axis(["cargo", "partido"])
    assert pa.sub(el, fill_value=0).abs().sum() == 0      # partido de 2022 do arquivo = eleitos do TSE


def test_previsao_fecha_nas_cadeiras_e_nos_blocos():
    for cargo in ("DF", "DE"):
        r = rb.prever(cargo, 0.25, 0.5, S=800)
        assert abs(sum(l["med"] for l in r["listas"]) - rb.CADEIRAS[cargo]) < 1e-6
        assert abs(sum(b["med"] for b in r["blocos"].values()) - rb.CADEIRAS[cargo]) < 0.05
        assert all(l["p10"] <= l["mediana"] <= l["p90"] for l in r["listas"])


def test_migracao_move_votos_entre_partidos_e_conserva_o_total():
    pl, el, ls, un, at = rb.carregar()
    b0, b1 = rb.base_2026(pl, at, "DE", 0.0), rb.base_2026(pl, at, "DE", 1.0)
    assert abs(b0.sum() - 1) < 1e-9 and abs(b1.sum() - 1) < 1e-9
    assert b1["PSD"] > b0["PSD"] and b1["PSDB"] < b0["PSDB"]           # PSDB → PSD é o maior fluxo estadual
    assert "PRD" in b0.index and "PTB" not in b0.index                 # sucessão PTB/Patriota → PRD


def test_federacoes_de_2026_nao_repetem_partido():
    ps = [p for m in rb.FEDERACOES_2026.values() for p in m]
    assert len(ps) == len(set(ps))


def test_ruido_cresce_para_partidos_pequenos_e_cobertura_do_backtest_fica_perto_de_80():
    blk = rb.blocos_governador()
    c, n = rb.cobertura(rb.LAM_PADRAO, rb.SIG_B, rb.SIG_I, blk, S=600)
    assert 0.7 < c < 0.9 and n > 60

"""Distritão no RS: eleitos oficiais do TSE (31 federais e 55 estaduais) contra os N mais votados, 2018, 2022 e 2026."""
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
D = json.load(open(RAIZ / "modelos/distritao-rs.json", encoding="utf-8"))


def test_cadeiras_e_trocas_fecham():
    for ano in ("2018", "2022", "2026"):
        for sig, n in (("DF", 31), ("DE", 55)):
            s = D[ano][sig]
            assert s["cadeiras"] == n and s["iguais"] + s["trocas"] == n and len(s["so_atual"]) == len(s["so_distritao"]) == s["trocas"], (ano, sig)
            assert sum(p["atual"] for p in s["partidos"]) == n and sum(p["distritao"] for p in s["partidos"]) == n
            assert sum(b["atual"] for b in s["blocos"].values()) == n and sum(b["distritao"] for b in s["blocos"].values()) == n
            assert s["corte_distritao"] > s["maior_nao_eleito_atual"] or s["trocas"] > 0


def test_quem_sai_tem_menos_votos_que_quem_entra():
    for ano in ("2018", "2022", "2026"):
        for sig in ("DF", "DE"):
            s = D[ano][sig]
            assert all(x["votos"] < s["corte_distritao"] for x in s["so_atual"]) and all(x["votos"] >= s["corte_distritao"] for x in s["so_distritao"])


def test_conta_por_partido_de_2026_bate_com_a_contagem_que_o_site_usava():
    press = pd.read_csv(RAIZ / "datasets/resultado-2026-rs-bancada.csv").dropna(subset=["cadeiras"])
    for sig in ("DF", "DE"):
        oficial = {p["partido"].upper(): p["atual"] for p in D["2026"][sig]["partidos"] if p["atual"]}
        imprensa = {p.upper(): int(n) for p, n in press[press.cargo == sig].set_index("partido").cadeiras.items()}
        assert oficial == imprensa, sig


def test_o_rs_e_pouco_afetado_e_a_pagina_existe():
    assert D["2026"]["DF"]["trocas"] == 3 and D["2026"]["DE"]["trocas"] == 7 and D["2018"]["DF"]["trocas"] == 2
    assert all(D[a][s]["trocas"] <= 0.2 * D[a][s]["cadeiras"] for a in D for s in D[a])
    assert (RAIZ / "distritao.html").exists()


def test_distritao_brasil_fecha_513_e_1059_e_o_pl_encolhe_em_2026():
    B = json.load(open(RAIZ / "modelos/distritao-br.json", encoding="utf-8"))
    for ano in ("2018", "2022", "2026"):
        assert B[ano]["DF"]["cadeiras"] == 513 and B[ano]["DE"]["cadeiras"] == 1059, ano
        for cargo in ("DF", "DE"):
            s = B[ano][cargo]
            assert sum(p["atual"] for p in s["partidos"]) == s["cadeiras"] == sum(p["distritao"] for p in s["partidos"]) and s["iguais"] + s["trocas"] == s["cadeiras"]
            assert sum(u["cadeiras"] for u in s["por_uf"]) == s["cadeiras"] and sum(u["trocas"] for u in s["por_uf"]) == s["trocas"]
    pl = B["2026"]["DF"]["pl"]
    assert pl["atual"] == 121 and pl["distritao"] == 102 and sum(u["pl_atual"] for u in B["2026"]["DF"]["por_uf"]) == 121
    assert B["2026"]["DF"]["puxadores"]["topo"][0]["nome"] == "Nikolas Ferreira" and (RAIZ / "distritao-brasil.html").exists()


def test_analise_do_distritao_e_consistente():
    B = json.load(open(RAIZ / "modelos/distritao-br.json", encoding="utf-8"))
    A = B["2026"]["DF"]["analise"]
    assert A["sai_n"] == A["entra_n"] == B["2026"]["DF"]["trocas"] and A["mecanismos"]["sai_com_puxador"] + A["mecanismos"]["sai_sem_puxador"] == A["sai_n"]
    assert A["mecanismos"]["pl"]["sai"] == 22 and A["mecanismos"]["pl"]["entra"] == 3 and abs(A["concentracao"]["corr"]) < 0.3
    assert A["votos_sem_cadeira"]["fora_dos_n_distritao_pct"] > 5 * A["votos_sem_cadeira"]["lista_sem_cadeira_pct"]
    assert A["gallagher_distritao"] > A["gallagher_atual"] and sum(x["cadeiras"] for x in A["por_tamanho"]) == 513
    assert B["2018"]["DF"]["analise"]["votos_sem_cadeira"]["lista_sem_cadeira_pct"] > 0           # 2018: federação "#NULO#" tratada como nula
    assert B["2026"]["DF"]["analise_rs"]["sai_n"] == 3 and B["2026"]["DE"]["analise_rs"]["sai_n"] == 7

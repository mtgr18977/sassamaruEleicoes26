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

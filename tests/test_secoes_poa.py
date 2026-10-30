"""Onde virou (seções, municípios, UFs) e Porto Alegre (zonas): os números vêm dos arquivos oficiais por seção e por zona e fecham com o resultado oficial."""
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
S = json.load(open(RAIZ / "modelos/secoes-2026.json", encoding="utf-8"))
P = json.load(open(RAIZ / "modelos/poa.json", encoding="utf-8"))


def test_secoes_fecham_com_o_resultado_oficial_e_o_exterior_fica_de_fora_da_analise():
    z = pd.read_csv(RAIZ / "datasets/tse-presidente-zona-2026.csv")
    assert z.lula_t2.sum() == 64_256_232 and z.flavio_t2.sum() == 59_826_041 and z.lula_t1.sum() == 53_879_538 and z.flavio_t1.sum() == 56_104_503
    dentro = z[z.uf != "ZZ"]
    assert dentro.lula_t2.sum() == S["brasil"]["lula_t2"] and dentro.flavio_t2.sum() == S["brasil"]["flavio_t2"]


def test_transicoes_somam_o_total_e_a_virada_e_de_lula():
    for escala, esperado in (("secao", S["brasil"]["secoes"]), ("municipio", S["brasil"]["municipios"]), ("zona", S["brasil"]["zonas"]), ("uf", 27)):
        assert sum(v["n"] for v in S["transicao"][escala].values()) == esperado, escala
    t = S["transicao"]
    assert t["secao"]["FL"]["n"] == 33_271 and t["secao"]["LF"]["n"] == 699 and t["municipio"]["FL"]["n"] == 213 and t["municipio"]["LF"]["n"] == 1
    assert t["uf"]["FL"]["n"] == 1 and t["uf"]["LF"]["n"] == 0 and next(u for u in S["ufs"] if u["uf"] == "MG")["w1"] == "F"


def test_ufs_regioes_e_ganhos_batem():
    b = S["brasil"]
    assert len(S["ufs"]) == 27 and all(u["dpp"] > 0 for u in S["ufs"])
    assert sum(u["dl"] for u in S["ufs"]) == b["dl"] and sum(u["df"] for u in S["ufs"]) == b["df"]
    assert sum(r["dl"] for r in S["regioes"]) == b["dl"]
    assert abs(b["l2"] - 100 * b["lula_t2"] / (b["lula_t2"] + b["flavio_t2"])) < 0.05
    v = S["vs2022"]
    assert v["mais_lula"] + v["menos_lula"] <= v["n"] and v["menos_lula"] > v["mais_lula"] and v["ponderada_pp"] > 0 > v["mediana_pp"]


def test_porto_alegre_bate_com_o_tse_e_tem_dez_zonas():
    c = P["cidade"]["presidente"]
    assert (c["2022_2"]["pt"], c["2022_2"]["adv"]) == (437_798, 380_499) and (c["2026_2"]["pt"], c["2026_2"]["adv"]) == (456_019, 360_690)
    assert len(P["zonas"]) == 10 and sorted(z["zona"] for z in P["zonas"]) == [1, 2, 111, 112, 113, 114, 158, 159, 160, 161]
    assert sum(z["presidente"]["2026_2"]["pt"] for z in P["zonas"]) == c["2026_2"]["pt"]
    assert sum(z["secoes"] for z in P["zonas"]) == P["secoes"]["n"] == sum(P["secoes"]["transicao"].values())
    gov = {x["candidato"]: x["votos"] for x in P["cidade"]["governador"]["2026_1"]}
    assert gov["Juliana Brizola"] == 338_394 and gov["Zucco"] == 324_823
    assert all(k["brizola"] is not None for k in P["casado"])


def test_paginas_novas_existem_e_estao_no_menu():
    import nav
    for h in ("onde-virou.html", "portoalegre.html"):
        assert h in [a[0] for a in nav.ABAS] and (RAIZ / h).exists()

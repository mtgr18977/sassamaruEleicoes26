import json

import analisar_redes as ar

D = json.load(open("datasets/redes/agregado-bluesky.json", encoding="utf-8"))


def test_intervalo_de_wilson():
    lo, hi = ar.wilson(38, 76)                      # 50% de 76: simétrico em torno de 50
    assert abs((lo + hi) / 2 - 50) < 0.5 and 15 < hi - lo < 25
    assert ar.wilson(0, 76)[0] == 0 and ar.wilson(76, 76)[1] == 100 and ar.wilson(0, 0) is None


def test_agregado_tem_o_que_a_pagina_usa_e_nao_guarda_textos_nem_autores():
    for k in ("volume", "debate_efeito", "globo", "corpus", "hashtags", "posicao", "avaliacao", "amostra_rotulada"):
        assert k in D
    assert len(D["posicao"]) == 6 and {p["periodo"] for p in D["posicao"]} >= {"antes do debate", "debate e depois", "Globo e depois"} and all(abs(sum(p[c]["pct"] for c in ("P", "N", "0")) - 100) < 0.2 for p in D["posicao"])
    g = D["globo"]
    assert set(g) >= {"efeito", "hashtags", "temas"} and any(h["h"] == "23/10 22h" and h["checagem_x"] > 5 for h in g["efeito"]["horas"])   # a palavra "checagem" disparou na hora do debate
    assert all(set(t) >= {"tema", "antes_pct", "depois_pct"} for t in g["temas"]["temas"])
    txt = json.dumps(D, ensure_ascii=False).lower()
    assert "bsky.social" not in txt and "did:plc" not in txt and "at://" not in txt          # sem @, DID nem endereço de post
    assert all(set(w) >= {"ini", "fim", "horas", "lula_ph", "flavio_ph"} for w in D["volume"]) and all(w["horas"] > 0 for w in D["volume"])
    assert D["avaliacao"]["modelos"][0]["nome"].startswith("Linha de base") and 0 < D["avaliacao"]["modelos"][0]["acuracia"] <= 1


def test_pagina_e_menu():
    import nav
    assert any(a[0] == "redes.html" for a in nav.ABAS)
    html = open("redes.html", encoding="utf-8").read()
    assert "Redes sociais" in html and "__DATA__" not in html and '"posicao"' in html

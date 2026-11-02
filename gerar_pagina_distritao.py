"""Gera distritao.html (aba "Distritão RS": e se o RS elegesse só os mais votados) a partir de apps/distritao.template.html.

Entradas: modelos/distritao-rs.json (distritao_rs.py) e a análise do RS dentro de modelos/distritao-br.json (distritao_br.py)."""
import json
from pathlib import Path

import nav

dados = json.load(open("modelos/distritao-rs.json", encoding="utf-8"))
br = json.load(open("modelos/distritao-br.json", encoding="utf-8"))
dados["analise_rs"] = {c: br["2026"][c]["analise_rs"] for c in ("DF", "DE")}
dados["brasil"] = {c: dict(trocas=br["2026"][c]["trocas"], cadeiras=br["2026"][c]["cadeiras"], razao=br["2026"][c]["analise"]["razao_media_entra_sai"]) for c in ("DF", "DE")}
html = nav.moldura(Path("apps/distritao.template.html").read_text(encoding="utf-8"), "distritao.html").replace("__DATA__", json.dumps(dados, ensure_ascii=False, separators=(",", ":")))
Path("distritao.html").write_text(html, encoding="utf-8")
print("distritao.html", len(html) // 1024, "KB")

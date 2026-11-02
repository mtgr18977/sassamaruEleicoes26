"""Gera distritao-brasil.html (aba "Distritão Brasil": e se cada UF elegesse deputados só pelos mais votados) a partir de apps/distritao-brasil.template.html.

Entrada: modelos/distritao-br.json (distritao_br.py)."""
import json
from pathlib import Path

import nav

dados = json.load(open("modelos/distritao-br.json", encoding="utf-8"))
html = nav.moldura(Path("apps/distritao-brasil.template.html").read_text(encoding="utf-8"), "distritao-brasil.html").replace("__DATA__", json.dumps(dados, ensure_ascii=False, separators=(",", ":")))
Path("distritao-brasil.html").write_text(html, encoding="utf-8")
print("distritao-brasil.html", len(html) // 1024, "KB")

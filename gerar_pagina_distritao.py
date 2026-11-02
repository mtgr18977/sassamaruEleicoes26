"""Gera distritao.html (aba "Distritão RS": e se o RS elegesse só os mais votados) a partir de apps/distritao.template.html.

Entrada: modelos/distritao-rs.json (distritao_rs.py)."""
import json
from pathlib import Path

import nav

dados = json.load(open("modelos/distritao-rs.json", encoding="utf-8"))
html = nav.moldura(Path("apps/distritao.template.html").read_text(encoding="utf-8"), "distritao.html").replace("__DATA__", json.dumps(dados, ensure_ascii=False, separators=(",", ":")))
Path("distritao.html").write_text(html, encoding="utf-8")
print("distritao.html", len(html) // 1024, "KB")

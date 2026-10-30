"""Gera portoalegre.html (aba "Porto Alegre": presidente e governador por zona eleitoral, 2018, 2022 e 2026) a partir de apps/portoalegre.template.html.

Entrada: modelos/poa.json (analisar_poa.py)."""
import json
from pathlib import Path

import nav

dados = json.load(open("modelos/poa.json", encoding="utf-8"))
html = nav.moldura(Path("apps/portoalegre.template.html").read_text(encoding="utf-8"), "portoalegre.html").replace("__DATA__", json.dumps(dados, ensure_ascii=False, separators=(",", ":")))
Path("portoalegre.html").write_text(html, encoding="utf-8")
print("portoalegre.html", len(html) // 1024, "KB")

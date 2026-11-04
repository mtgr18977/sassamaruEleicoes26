"""Gera colegio-eleitoral.html (aba "Colégio Eleitoral": e se o presidente fosse eleito como nos EUA, com delegados e distritos) a partir de apps/colegio-eleitoral.template.html.

Entrada: modelos/colegio-eleitoral.json (colegio_eleitoral.py)."""
import json
from pathlib import Path

import nav

dados = json.load(open("modelos/colegio-eleitoral.json", encoding="utf-8"))
html = nav.moldura(Path("apps/colegio-eleitoral.template.html").read_text(encoding="utf-8"), "colegio-eleitoral.html").replace("__DATA__", json.dumps(dados, ensure_ascii=False, separators=(",", ":")))
Path("colegio-eleitoral.html").write_text(html, encoding="utf-8")
print("colegio-eleitoral.html", len(html) // 1024, "KB")

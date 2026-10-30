"""Gera onde-virou.html (aba "Onde virou": 1º × 2º turno de 2026 por seção, zona, município e UF) a partir de apps/onde-virou.template.html.

Entrada: modelos/secoes-2026.json (analisar_secoes_2026.py, que lê os boletins de urna por seção de fetch_tse_secoes.py)."""
import json
from pathlib import Path

import nav

dados = json.load(open("modelos/secoes-2026.json", encoding="utf-8"))
html = nav.moldura(Path("apps/onde-virou.template.html").read_text(encoding="utf-8"), "onde-virou.html").replace("__DATA__", json.dumps(dados, ensure_ascii=False, separators=(",", ":")))
Path("onde-virou.html").write_text(html, encoding="utf-8")
print("onde-virou.html", len(html) // 1024, "KB")

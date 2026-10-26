"""Gera resultado.html (aba "Resultado": o resultado do 2º turno de 2026 contra o que o modelo e as pesquisas projetavam) a partir de apps/resultado.template.html.

Entrada: modelos/avaliacao-2turno.json (feito por avaliar_2turno.py a partir de datasets/resultado-2026-turno2.csv, do modelo e das pesquisas).
Roda em atualizar.py depois de sensibilidade; para atualizar com o resultado oficial do TSE: troque o CSV, rode avaliar_2turno.py e este script."""
import json
from pathlib import Path

import nav

dados = json.load(open("modelos/avaliacao-2turno.json", encoding="utf-8"))
html = nav.moldura(Path("apps/resultado.template.html").read_text(encoding="utf-8"), "resultado.html").replace("__DATA__", json.dumps(dados, ensure_ascii=False))
Path("resultado.html").write_text(html, encoding="utf-8")
print("resultado.html", len(html) // 1024, "KB")

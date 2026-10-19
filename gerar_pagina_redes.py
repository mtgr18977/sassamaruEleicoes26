"""Gera redes.html (aba "Redes sociais": a conversa no Bluesky sobre Lula e Flávio no 2º turno, com o debate de 18/10) a partir de apps/redes.template.html.

Entrada: datasets/redes/agregado-bluesky.json (feito por analisar_redes.py a partir do cache local de posts; sem textos, @ nem nomes de autores).
Não depende do cache: o site é gerado só com o agregado. Para atualizar os números: coletar_redes.py → analisar_redes.py → atualizar.py."""
import json
from pathlib import Path

import nav

dados = json.load(open("datasets/redes/agregado-bluesky.json", encoding="utf-8"))
html = nav.moldura(Path("apps/redes.template.html").read_text(encoding="utf-8"), "redes.html").replace("__DATA__", json.dumps(dados, ensure_ascii=False))
Path("redes.html").write_text(html, encoding="utf-8")
print("redes.html", len(html) // 1024, "KB")

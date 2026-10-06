"""Gera analise-senado.html (análise do Senado, 1º turno de 2026) a partir de apps/analise-senado.template.html e senado.py."""
import json

import nav
import senado


def main():
    dados = senado.construir()
    html = open("apps/analise-senado.template.html", encoding="utf-8").read().replace("__NAV__", nav.html("analise-senado.html")).replace("__DATA__", json.dumps(dados, ensure_ascii=False))
    open("analise-senado.html", "w", encoding="utf-8").write(html)
    print("analise-senado.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    main()

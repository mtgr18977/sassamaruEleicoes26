"""Menu de abas do site (uma só definição). Os geradores trocam __NAV__ nos templates; documentacao.html (estática) é reescrita por `python nav.py`."""
import re
from pathlib import Path

ABAS = [("segundo-turno.html", "2º turno"), ("index.html", "Presidente 2026"), ("analise.html", "Análise"), ("rs.html", "Governo do RS 2026"),
        ("analise-governo.html", "Análise do governo RS"), ("bancada.html", "Bancada RS 2026"), ("analise-bancada.html", "Análise da bancada RS"),
        ("analise-senado.html", "Análise do Senado"), ("documentacao.html", "Documentação")]


def html(pagina: str) -> str:
    return "".join(f'<a href="{h}"' + (' aria-current="page"' if h == pagina else "") + f">{t}</a>" for h, t in ABAS)


def reescrever(arq: str) -> None:
    p = Path(arq)
    s = p.read_text(encoding="utf-8")
    p.write_text(re.sub(r'(<nav class="tabs"[^>]*>).*?(</nav>)', lambda m: m.group(1) + html(Path(arq).name) + m.group(2), s, count=1, flags=re.S), encoding="utf-8")


if __name__ == "__main__":
    reescrever("documentacao.html")

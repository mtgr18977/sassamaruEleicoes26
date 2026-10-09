"""Moldura comum do site (uma só definição): cabeçalho, menu de abas agrupado e rodapé.

Os geradores leem o template, passam por `moldura(html, pagina)` e só então trocam __DATA__. A moldura troca o menu-placeholder
(`<nav class="tabs" ...>__NAV__</nav>`) por cabeçalho + menu, leva o botão de tema (`#tema`) para o cabeçalho e põe o rodapé depois de </main>.
`python nav.py` gera documentacao.html a partir de apps/documentacao.template.html."""
import datetime
import re
from pathlib import Path

# (arquivo, rótulo, grupo). A ordem é a do menu: Presidente primeiro, 2º turno depois.
ABAS = [("index.html", "Presidente 2026", "Presidente"), ("segundo-turno.html", "2º turno", "Presidente"), ("analise.html", "Análise", "Presidente"),
        ("rs.html", "Governo do RS 2026", "Rio Grande do Sul"), ("analise-governo.html", "Análise do governo RS", "Rio Grande do Sul"),
        ("bancada.html", "Bancada RS 2026", "Rio Grande do Sul"), ("analise-bancada.html", "Análise da bancada RS", "Rio Grande do Sul"),
        ("analise-senado.html", "Análise do Senado", "Senado"), ("analise-modelo.html", "Análise do modelo", "Análise do modelo"), ("documentacao.html", "Documentação", "Sobre")]
GITHUB = "https://github.com/mtgr18977/sassamaruEleicoes26"
PLACEHOLDER = '<nav class="tabs" aria-label="Seções do site">__NAV__</nav>'
BOTAO_TEMA = re.compile(r'<button id="tema"[^>]*>\s*</button>')
ICONE = ('<svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true"><rect x="2" y="11" width="6" height="11" rx="1.6" fill="var(--anti)"/>'
         '<rect x="9" y="3" width="6" height="19" rx="1.6" fill="var(--pt)"/><rect x="16" y="8" width="6" height="14" rx="1.6" fill="var(--s4)"/></svg>')


def html(pagina: str) -> str:
    """Só o miolo do <nav>: um bloco por grupo (rótulo + links)."""
    grupos: dict[str, list[str]] = {}
    for h, t, g in ABAS:
        grupos.setdefault(g, []).append(f'<a href="{h}"' + (' aria-current="page"' if h == pagina else "") + f">{t}</a>")
    return "".join(f'<span class="g"><span class="grp">{g}</span><span class="gl">{"".join(links)}</span></span>' for g, links in grupos.items())


def cabecalho(pagina: str, botao_tema: str) -> str:
    return ('<header class="mast"><a class="brand" href="index.html">' + ICONE + '<span><b>Eleições 2026</b><small>Dados, modelos e análises do Brasil e do RS</small></span></a>'
            + botao_tema + "</header>" + f'<nav class="tabs" aria-label="Seções do site">{html(pagina)}</nav>')


def rodape() -> str:
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    return ('<footer class="rodape"><div class="rodape-in">'
            "<p><b>Isto não é pesquisa eleitoral nem previsão validada.</b> É um modelo estatístico condicionado às pesquisas e ao histórico do TSE; "
            "pesquisas e resultados de 2026 nem sempre foram conferidos na fonte oficial, e cada página diz o que foi e o que não foi.</p>"
            f'<p>Fontes: TSE (resultados e dados abertos), API de Dados Abertos do Senado e da Câmara, institutos de pesquisa e imprensa, conforme a <a href="documentacao.html">documentação</a>. '
            f'Código aberto (MIT) em <a href="{GITHUB}" target="_blank" rel="noopener">GitHub</a>. Página gerada em {hoje}.</p></div></footer>')


def moldura(pagina_html: str, pagina: str) -> str:
    """Aplica cabeçalho, menu e rodapé a um template (ainda com __DATA__)."""
    assert PLACEHOLDER in pagina_html, f"{pagina}: template sem o menu-placeholder"
    botao = BOTAO_TEMA.search(pagina_html)
    tema = botao.group(0) if botao else '<button id="tema" class="tema" type="button" aria-label="Alternar tema claro/escuro"></button>'
    s = BOTAO_TEMA.sub("", pagina_html)
    s = s.replace(PLACEHOLDER, cabecalho(pagina, tema), 1)
    s = s.replace("<body>", '<body>\n<a class="pular" href="#conteudo">Pular para o conteúdo</a>', 1).replace("<main>", '<main id="conteudo">', 1)
    return s.replace("</main>", "</main>\n" + rodape(), 1)


def gerar_documentacao() -> None:
    s = moldura(Path("apps/documentacao.template.html").read_text(encoding="utf-8"), "documentacao.html")
    Path("documentacao.html").write_text(s, encoding="utf-8")
    print("documentacao.html", len(s) // 1024, "KB")


if __name__ == "__main__":
    gerar_documentacao()

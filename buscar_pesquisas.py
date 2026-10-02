"""Busca pesquisas novas em páginas HTML (tabelas da Wikipedia) e grava CANDIDATAS em datasets/candidatas.csv.

  python buscar_pesquisas.py                       # baixa a página da Wikipedia (presidente) e compara com o CSV oficial
  python buscar_pesquisas.py --url URL             # outra página (ex.: a do governador do RS não é suportada ainda)
  python buscar_pesquisas.py --html pagina.html    # página salva à mão (útil sem rede)

NÃO altera datasets/pesquisas-2026.csv. Cada candidata tem `status`:
  nova        instituto + data final que não existem no CSV
  divergente  mesmo instituto e mesma data final (ou campo_ini), mas números diferentes: conferir na fonte antes de qualquer coisa
Duplicadas idênticas são descartadas. Institutos fora dos quatro do modelo só entram com --todos.
Depois de conferir (registro no TSE, matéria ou relatório), copie a linha para pesquisas-2026.csv (sem fonte_url/status), preencha
`obs` e rode `python atualizar.py`. Regra do projeto: sem fonte, célula vazia.
"""
import argparse
import csv
import re
import ssl
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

URL_PADRAO = "https://pt.wikipedia.org/wiki/Pesquisas_de_opini%C3%A3o_para_a_elei%C3%A7%C3%A3o_presidencial_no_Brasil_em_2026"
CSV_OFICIAL = "datasets/pesquisas-2026.csv"
CSV_SAIDA = "datasets/candidatas.csv"
INSTITUTOS = {"datafolha": "Datafolha", "quaest": "Quaest", "atlas": "AtlasIntel", "real time": "RealTimeBigData", "rtbd": "RealTimeBigData"}
MESES = {m: i for i, m in enumerate(["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"], 1)}
CANDS = {"lula": "lula", "flavio": "flavio", "caiado": "caiado", "zema": "zema", "renan": "renan", "cury": "cury"}
NUMERICAS = ["t1_lula", "t1_flavio", "t1_caiado", "t1_zema", "t1_renan", "t1_cury", "t1_outros", "t1_bnin", "t2_lula", "t2_flavio", "t2_bnin"]


class _Tabelas(HTMLParser):
    """Extrai todas as <table> como listas de linhas de texto, expandindo colspan e rowspan."""

    def __init__(self):
        super().__init__()
        self.tabelas, self._t, self._lin, self._cel, self._span = [], None, None, None, {}

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == "table":
            self._t, self._span = [], {}
        elif tag == "tr" and self._t is not None:
            self._lin = []
        elif tag in ("td", "th") and self._lin is not None:
            self._cel = dict(texto="", cs=int(re.sub(r"\D", "", a.get("colspan", "1")) or 1), rs=int(re.sub(r"\D", "", a.get("rowspan", "1")) or 1))
        elif tag == "br" and self._cel is not None:
            self._cel["texto"] += " "

    def handle_data(self, d):
        if self._cel is not None:
            self._cel["texto"] += d

    def _preencher_spans(self):
        while len(self._lin) in self._span:
            txt, resta = self._span[len(self._lin)]
            self._lin.append(txt)
            if resta > 1:
                self._span[len(self._lin) - 1] = (txt, resta - 1)
            else:
                del self._span[len(self._lin) - 1]

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cel is not None:
            self._preencher_spans()
            txt = re.sub(r"\[[^\]]*\]", "", self._cel["texto"])
            txt = re.sub(r"\s+", " ", txt).strip()
            for _ in range(self._cel["cs"]):
                self._lin.append(txt)
                if self._cel["rs"] > 1:
                    self._span[len(self._lin) - 1] = (txt, self._cel["rs"] - 1)
            self._cel = None
        elif tag == "tr" and self._lin is not None:
            self._preencher_spans()
            if self._lin:
                self._t.append(self._lin)
            self._lin = None
        elif tag == "table" and self._t is not None:
            self.tabelas.append(self._t)
            self._t = None


def tabelas(html):
    p = _Tabelas()
    p.feed(html)
    return p.tabelas


def _sem_acento(s):
    return s.lower().translate(str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc"))


def numero(s):
    m = re.search(r"\d+(?:[.,]\d+)?", s or "")
    return float(m.group().replace(",", ".")) if m else None


def instituto(s):
    low = _sem_acento(s or "")
    for k, v in INSTITUTOS.items():
        if k in low:
            return v, True
    return (s or "").strip(), False


def periodo(s, ano=2026):
    """'22–23 set 2026', '27 set – 2 out', '26 a 30/9' -> (campo_ini, campo_fim) ISO ou (None, None)."""
    s = _sem_acento(s or "")
    s = re.sub(r"\bde\b", " ", s)
    m = re.search(r"(\d{1,2})\s*(?:/\s*(\d{1,2})|([a-z]{3})[a-z]*\.?)?\s*(?:-|–|—|a|ate)\s*(\d{1,2})\s*(?:/\s*(\d{1,2})|([a-z]{3})[a-z]*\.?)", s)
    um = re.search(r"(\d{1,2})\s*(?:/\s*(\d{1,2})|([a-z]{3})[a-z]*\.?)", s)
    y = re.search(r"\b(20\d\d)\b", s)
    ano = int(y.group(1)) if y else ano

    def mes(n, t):
        return int(n) if n else MESES.get(t)

    if m:
        d1, n1, t1, d2, n2, t2 = m.groups()
        m2 = mes(n2, t2)
        m1 = mes(n1, t1) or m2
        if m1 and m2:
            ini = f"{ano}-{m1:02d}-{int(d1):02d}"
            fim = f"{ano}-{m2:02d}-{int(d2):02d}"
            return ini, fim
    if um:
        d, n, t = um.groups()
        mm = mes(n, t)
        if mm:
            iso = f"{ano}-{mm:02d}-{int(d):02d}"
            return iso, iso
    return None, None


def extrair(html, url=""):
    """Linhas candidatas (dict com as colunas do CSV oficial) das tabelas que citam Lula e Flávio."""
    por_chave = {}
    for t in tabelas(html):
        cab = next((i for i, l in enumerate(t) if sum(1 for c in l if "lula" in _sem_acento(c)) and any("flavio" in _sem_acento(c) for c in l)), None)
        if cab is None:
            continue
        head = [_sem_acento(c) for c in t[cab]]
        col = {}
        for i, h in enumerate(head):
            for k, v in CANDS.items():
                if k in h:
                    col.setdefault(v, i)
            if re.search(r"instituto|pesquisa|empresa|fonte", h):
                col.setdefault("inst", i)
            if re.search(r"data|periodo|campo", h):
                col.setdefault("data", i)
            if re.search(r"amostra|entrevist", h):
                col.setdefault("n", i)
            if re.search(r"branco|nulo|indecis|ns/nr|nao sabe", h):
                col.setdefault("bnin", i)
            if re.search(r"outros", h):
                col.setdefault("outros", i)
        if not {"inst", "data", "lula", "flavio"} <= col.keys():
            continue
        turno = 1 if {"caiado", "zema"} & col.keys() else 2
        for lin in t[cab + 1:]:
            if len(lin) <= max(col.values()):
                continue
            nome, _ = instituto(lin[col["inst"]])
            ini, fim = periodo(lin[col["data"]])
            if not nome or not fim:
                continue
            r = por_chave.setdefault((nome, fim), dict(instituto=nome, campo_ini=ini, campo_fim=fim))
            r.setdefault("fonte_url", url)
            if "n" in col:
                n = numero(lin[col["n"]].replace(".", "")) if re.search(r"\d", lin[col["n"]]) else None
                if n:
                    r.setdefault("amostra", int(n))
            for k, nome_col in (("lula", "lula"), ("flavio", "flavio"), ("caiado", "caiado"), ("zema", "zema"), ("renan", "renan"), ("cury", "cury"), ("outros", "outros"), ("bnin", "bnin")):
                if k in col:
                    v = numero(lin[col[k]])
                    if v is not None:
                        r[f"t{turno}_{nome_col}"] = v
    return list(por_chave.values())


def comparar(candidatas, oficial, todos=False, desde="2026-07-01"):
    """Classifica cada candidata contra o CSV oficial (lista de dicts). Retorna só 'nova' e 'divergente'."""
    saida = []
    for c in candidatas:
        if c["campo_fim"] < desde:
            continue
        if not instituto(c["instituto"])[1] and not todos:
            continue
        mesmo = [o for o in oficial if o["instituto"] == c["instituto"] and (o["campo_fim"] == c["campo_fim"] or o["campo_ini"] == c["campo_ini"])]
        if not mesmo:
            saida.append({**c, "status": "nova"})
            continue
        o = mesmo[0]
        difs = [k for k in NUMERICAS if k in c and o.get(k) not in (None, "") and abs(float(o[k]) - c[k]) > 0.51]
        if difs:
            saida.append({**c, "status": "divergente", "obs": "difere do CSV em " + ", ".join(f"{k}: {o[k]} vs {c[k]:g}" for k in difs)})
    return saida


def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "sassamaru-eleicoes/1.0 (pesquisa academica)"})
    with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
        return r.read().decode("utf-8", "replace")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=URL_PADRAO)
    ap.add_argument("--html", help="arquivo HTML local em vez de baixar")
    ap.add_argument("--todos", action="store_true", help="inclui institutos fora dos quatro do modelo")
    ap.add_argument("--desde", default="2026-07-01")
    ap.add_argument("--oficial", default=CSV_OFICIAL)
    ap.add_argument("--saida", default=CSV_SAIDA)
    a = ap.parse_args(argv)
    try:
        html = Path(a.html).read_text(encoding="utf-8") if a.html else baixar(a.url)
    except OSError as e:     # URLError é OSError: rede bloqueada (proxy/egress) ou arquivo ausente
        print(f"Não consegui obter a página ({e}). Sem rede, salve o HTML no navegador e use --html arquivo.html", file=sys.stderr)
        return 1
    with open(a.oficial, newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        colunas, oficial = leitor.fieldnames, list(leitor)
    cands = comparar(extrair(html, a.url if not a.html else a.html), oficial, a.todos, a.desde)
    cands.sort(key=lambda c: (c["campo_fim"], c["instituto"]))
    with open(a.saida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[*colunas[:-1], "obs", "fonte_url", "status"], extrasaction="ignore")
        w.writeheader()
        w.writerows(cands)
    print(f"{len(cands)} candidata(s) em {a.saida} (o CSV oficial não foi alterado)")
    for c in cands:
        print(f"  [{c['status']}] {c['instituto']} {c['campo_ini']}..{c['campo_fim']}  Lula {c.get('t1_lula', '-')} x Flávio {c.get('t1_flavio', '-')}  {c.get('obs', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

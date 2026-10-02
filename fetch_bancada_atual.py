"""Partido ATUAL dos deputados eleitos em 2022 pelo RS (federais e estaduais). Saída: datasets/rs-bancada-atual.csv.

Fontes (anotadas em cada linha):
  - Dep. Federal: API de Dados Abertos da Câmara (partido do último status de cada deputado da 57ª legislatura pelo RS),
    pareada com os eleitos do TSE pelo nome civil / nome de urna.
  - Dep. Estadual: lista da 56ª legislatura na Wikipédia (colaborativa; traz o histórico de partidos de cada deputado),
    pareada com os eleitos do TSE pelos votos nominais (número exato). NÃO conferida com o site da Assembleia.
O CSV é versionado; rode este script (com rede) só para atualizar. Mostra o que não pareou: nada é preenchido por palpite.
"""
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date

import pandas as pd

import fetch_tse_legislativo as ft

SAIDA = "datasets/rs-bancada-atual.csv"
UA = {"User-Agent": "sassamaru-eleicoes/1.0 (dados abertos)", "Accept": "application/json"}
WIKI = "Lista de deputados estaduais do Rio Grande do Sul da 56.ª legislatura"
PARTIDO = {"Republicanos": "REPUBLICANOS", "PC do B": "PCdoB", "PCdoB": "PCdoB", "Podemos": "PODE", "PODE": "PODE", "UNIÃO": "UNIÃO", "União Brasil": "UNIÃO"}
norm = lambda s: re.sub(r"[^A-Z ]", "", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()).strip()
sigla = lambda p: PARTIDO.get(p.strip(), p.strip())


def get(url, tentativas=5):
    for k in range(tentativas):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode()
        except Exception as e:                      # 429/504 da Wikipédia e da API da Câmara: espera e repete
            print("repetindo", k, str(e)[:60])
            time.sleep(2 ** (k + 1))
    raise SystemExit("falhou: " + url)


def eleitos_tse(cargo: str) -> pd.DataFrame:
    """Eleitos de 2022 com votos nominais (somados nas zonas), nome civil e de urna."""
    usar = ["DS_CARGO", "SQ_CANDIDATO", "NM_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO", "DS_SIT_TOT_TURNO", "QT_VOTOS_NOMINAIS_VALIDOS"]
    d = pd.concat(ch[ch.DS_CARGO == ("Deputado Federal" if cargo == "DF" else "Deputado Estadual")]
                  for ch in pd.read_csv(ft.arquivo_rs("votacao_candidato_munzona", 2022), sep=";", encoding="latin-1", dtype=str, usecols=usar, chunksize=ft.CHUNK))
    d["votos"] = pd.to_numeric(d.QT_VOTOS_NOMINAIS_VALIDOS, errors="coerce").fillna(0)
    g = d.groupby(["SQ_CANDIDATO", "NM_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO", "DS_SIT_TOT_TURNO"], as_index=False).votos.sum()
    g = g[g.DS_SIT_TOT_TURNO.str.upper().str.startswith("ELEITO")].copy()
    g["votos"] = g.votos.astype(int)
    return g


def federais() -> pd.DataFrame:
    base = "https://dadosabertos.camara.leg.br/api/v2/deputados"
    lista = json.loads(get(f"{base}?siglaUf=RS&idLegislatura=57&itens=100"))["dados"]
    cam = []
    for x in lista:
        u = json.loads(get(f"{base}/{x['id']}"))["dados"]
        cam.append(dict(civil=u.get("nomeCivil"), urna=u["ultimoStatus"]["nomeEleitoral"], partido=u["ultimoStatus"]["siglaPartido"]))
    el, linhas = eleitos_tse("DF"), []
    for r in el.itertuples():
        m = [c for c in cam if norm(c["civil"]) == norm(r.NM_CANDIDATO)] or [c for c in cam if norm(c["urna"]) == norm(r.NM_URNA_CANDIDATO)]
        linhas.append(dict(cargo="DF", nome=r.NM_URNA_CANDIDATO.title(), votos_2022=r.votos, partido_2022=sigla(r.SG_PARTIDO),
                           partido_atual=sigla(m[0]["partido"]) if m else None, fonte="API da Câmara (dados abertos)"))
    return pd.DataFrame(linhas)


def estaduais(texto: str | None = None) -> pd.DataFrame:
    if texto is None:
        texto = get("https://pt.wikipedia.org/w/index.php?" + urllib.parse.urlencode({"title": WIKI, "action": "raw"}))
    corpo = texto[texto.index("== Deputados Estaduais"):]
    wiki = []
    for r in corpo.split("\n|-")[1:]:
        c = [x.strip() for x in r.replace("\n", " ").split("||")]
        if len(c) < 4:
            continue
        nome = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", c[0])
        nome = re.sub(r"^.*?'''", "", nome).replace("'''", "").strip(" |")
        partidos = re.findall(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", c[1])
        v = re.sub(r"\D", "", re.split(r"<ref", c[3])[0])
        if partidos and v:
            wiki.append(dict(nome=nome, votos=int(v), partido=sigla(partidos[-1])))
    w = pd.DataFrame(wiki)
    el = eleitos_tse("DE")
    m = el.merge(w, on="votos", how="left", validate="1:1")
    return pd.DataFrame(dict(cargo="DE", nome=m.NM_URNA_CANDIDATO.str.title(), votos_2022=m.votos, partido_2022=m.SG_PARTIDO.map(sigla),
                             partido_atual=m.partido, fonte="Wikipédia (56ª legislatura), não conferida com a ALRS"))


def main():
    d = pd.concat([federais(), estaduais()], ignore_index=True)
    d["acesso"] = str(date.today())
    sem = d[d.partido_atual.isna()]
    print(len(d), "eleitos;", len(sem), "sem partido atual:", sem.nome.tolist())
    d.to_csv(SAIDA, index=False)
    print(d.groupby(["cargo", "partido_atual"]).size().unstack(0).fillna(0).astype(int).to_string())


if __name__ == "__main__":
    main()

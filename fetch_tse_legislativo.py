"""Deputado Federal e Estadual do RS (2002–2022): votos por partido e unidade regional, listas (coligação/federação) e eleitos.

Baixa só o arquivo *_RS.csv de cada zip do TSE por requisição parcial (remotezip: `pip install remotezip`), sem baixar os
zips de ~500 MB. Se já houver zips em datasets/tse_raw/, usa o arquivo de lá (mesmo critério de fetch_tse.py).

Saídas (datasets/):
  tse-legislativo-rs-partido.csv  ano, cargo, unidade, partido, votos            (nominais + legenda válidos; unidade = rs_dados)
  tse-legislativo-rs-partido-lista.csv  ano, cargo, partido, lista, votos   (a que lista cada partido pertencia)
  tse-legislativo-rs-listas.csv   ano, cargo, lista, tipo, composicao, votos, cadeiras   (unidade de disputa das cadeiras)
  tse-legislativo-rs-eleitos.csv  ano, cargo, partido, lista, cadeiras           (eleitos por partido, do arquivo de candidatos)
"""
import zipfile
from pathlib import Path

import pandas as pd

RAW = Path("datasets/tse_raw")
BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
CARGOS = {"Deputado Federal": "DF", "Deputado Estadual": "DE"}
ANOS = range(2002, 2023, 4)
CHUNK = 200_000


def arquivo_rs(nome: str, ano: int) -> Path:
    """Caminho do CSV do RS: já extraído, dentro de um zip local, ou extraído por requisição parcial do zip do TSE."""
    RAW.mkdir(parents=True, exist_ok=True)
    alvo = RAW / f"{nome}_{ano}_RS.csv"
    if alvo.exists():
        return alvo
    zip_local = RAW / f"{nome}_{ano}.zip"
    if zip_local.exists():
        with zipfile.ZipFile(zip_local) as zf:
            membro = [n for n in zf.namelist() if n.upper().endswith(("_RS.CSV", "_RS.TXT"))][0]
            alvo.write_bytes(zf.read(membro))
        return alvo
    from remotezip import RemoteZip
    with RemoteZip(f"{BASE}/{nome}/{nome}_{ano}.zip") as z:
        membro = [i for i in z.infolist() if i.filename.upper().endswith(("_RS.CSV", "_RS.TXT"))][0]
        z.extract(membro, RAW)
        (RAW / membro.filename).rename(alvo)
    return alvo


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)


def ler_partidos(ano: int) -> pd.DataFrame:
    """Votos válidos (nominais + legenda) por município, cargo, partido e lista."""
    d = pd.read_csv(arquivo_rs("votacao_partido_munzona", ano), sep=";", encoding="latin-1", dtype=str)
    d = d[d.DS_CARGO.isin(CARGOS)].copy()
    if "QT_TOTAL_VOTOS_LEG_VALIDOS" in d:     # 2018 em diante: colunas de votos válidos
        d["votos"] = _num(d.QT_TOTAL_VOTOS_LEG_VALIDOS) + _num(d.QT_VOTOS_NOMINAIS_VALIDOS)
    else:
        d["votos"] = _num(d.QT_VOTOS_NOMINAIS) + _num(d.QT_VOTOS_LEGENDA)
    isolado = d.TP_AGREMIACAO.str.upper().str.startswith("P")        # "Partido isolado" / "P"
    d["lista"] = (d.SG_PARTIDO.where(isolado, d.SQ_COLIGACAO.astype(str)))
    d["tipo"] = isolado.map({True: "isolado", False: "coligacao"})
    if "SG_FEDERACAO" in d:
        d.loc[d.TP_AGREMIACAO.str.upper().str.startswith("F"), "tipo"] = "federacao"
    comp = d.DS_COMPOSICAO_FEDERACAO if "DS_COMPOSICAO_FEDERACAO" in d else None
    d["composicao"] = d.DS_COMPOSICAO_COLIGACAO if comp is None else d.DS_COMPOSICAO_COLIGACAO.where(d.tipo != "federacao", comp)
    d["nome_lista"] = d.NM_COLIGACAO if "NM_COLIGACAO" in d else ""
    d["cod_municipio"] = d.CD_MUNICIPIO.str.strip().str.zfill(5)
    d["cargo"] = d.DS_CARGO.map(CARGOS)
    d["partido"] = d.SG_PARTIDO.str.strip()
    d["ano"] = ano
    return d[["ano", "cargo", "cod_municipio", "partido", "lista", "tipo", "composicao", "nome_lista", "votos"]]


def lista_do_partido(partidos: pd.DataFrame) -> pd.DataFrame:
    """(cargo, partido) -> lista (coligação, federação ou o próprio partido) com os votos do partido na lista.
    Em 2002 há linhas "isoladas" de poucos votos de partidos que concorreram coligados: vale a lista com mais votos."""
    mapa = partidos.groupby(["cargo", "partido", "lista"], as_index=False).votos.sum()
    return mapa.sort_values("votos").drop_duplicates(["cargo", "partido"], keep="last")


def ler_eleitos(ano: int, partidos: pd.DataFrame) -> pd.DataFrame:
    """Candidatos eleitos (um por SQ_CANDIDATO), com a lista do partido tirada do arquivo de partidos.
    (O código da coligação do arquivo de candidatos não bate com o de partidos em 2006/2010; o partido identifica a lista.)"""
    mapa = lista_do_partido(partidos)
    usar = ["DS_CARGO", "SQ_CANDIDATO", "SG_PARTIDO", "DS_SIT_TOT_TURNO"]
    partes = []
    for ch in pd.read_csv(arquivo_rs("votacao_candidato_munzona", ano), sep=";", encoding="latin-1", dtype=str, usecols=usar, chunksize=CHUNK):
        ch = ch[ch.DS_CARGO.isin(CARGOS) & ch.DS_SIT_TOT_TURNO.str.upper().str.startswith(("ELEITO", "MÉDIA", "MEDIA"))]   # 2002–2010: "MÉDIA" = eleito por média
        if len(ch):
            partes.append(ch.drop_duplicates("SQ_CANDIDATO"))
    d = pd.concat(partes).drop_duplicates("SQ_CANDIDATO")
    d["cargo"] = d.DS_CARGO.map(CARGOS)
    d["partido"] = d.SG_PARTIDO.str.strip()
    d = d.merge(mapa[["cargo", "partido", "lista"]], on=["cargo", "partido"], how="left")
    assert d.lista.notna().all(), f"eleito sem lista em {ano}"
    d["ano"] = ano
    return d.groupby(["ano", "cargo", "partido", "lista"], as_index=False).size().rename(columns={"size": "cadeiras"})


def main():
    reg = pd.read_csv("datasets/rs-municipios-regioes.csv", dtype={"cod_municipio": str})
    import rs_dados
    reg["unidade"] = reg.meso
    reg.loc[reg.municipio == "PORTO ALEGRE", "unidade"] = "Porto Alegre"
    reg.loc[(reg.meso == "Metropolitana de Porto Alegre") & (reg.municipio != "PORTO ALEGRE"), "unidade"] = "Metropolitana (sem POA)"
    reg["unidade"] = reg.unidade.map(rs_dados.NOME_UNIDADE)
    part, listas, eleitos, pl = [], [], [], []
    for ano in ANOS:
        p = ler_partidos(ano)
        e = ler_eleitos(ano, p)
        assert p.cod_municipio.isin(reg.cod_municipio).all(), f"município sem região em {ano}"
        pu = p.merge(reg[["cod_municipio", "unidade"]], on="cod_municipio").groupby(["ano", "cargo", "unidade", "partido"], as_index=False).votos.sum()
        part.append(pu)
        pl.append(lista_do_partido(p).assign(ano=ano))
        lp = p.groupby(["ano", "cargo", "lista", "tipo"], as_index=False).agg(votos=("votos", "sum"), composicao=("composicao", "first"), nome=("nome_lista", "first"))
        le = e.groupby(["ano", "cargo", "lista"], as_index=False).cadeiras.sum()
        listas.append(lp.merge(le, on=["ano", "cargo", "lista"], how="left").fillna({"cadeiras": 0}))
        eleitos.append(e)
        print(ano, "ok", {c: int(e[e.cargo == c].cadeiras.sum()) for c in ("DF", "DE")})
    D = "datasets/"
    pd.concat(part).to_csv(D + "tse-legislativo-rs-partido.csv", index=False)
    pd.concat(pl)[["ano", "cargo", "partido", "lista", "votos"]].to_csv(D + "tse-legislativo-rs-partido-lista.csv", index=False)
    l = pd.concat(listas)
    l["cadeiras"] = l.cadeiras.astype(int)
    l.to_csv(D + "tse-legislativo-rs-listas.csv", index=False)
    pd.concat(eleitos).to_csv(D + "tse-legislativo-rs-eleitos.csv", index=False)


if __name__ == "__main__":
    main()

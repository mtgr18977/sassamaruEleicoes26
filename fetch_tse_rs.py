"""Extrai a votação para GOVERNADOR do RS (2002–2022) dos zips do TSE já baixados em datasets/tse_raw/.

Lê só o arquivo *_RS.csv de cada zip (os arquivos _BR/_BRASIL repetem linhas de outros cargos) e soma zonas por
(ano, turno, município, candidato). Saída: datasets/tse-governador-rs-municipio.csv.
"""
import zipfile
from pathlib import Path

import pandas as pd

from fetch_tse import ALIASES_CANDIDATO, CHUNK, mapear_colunas, normalizar_texto

RAW, SAIDA = Path("datasets/tse_raw"), Path("datasets/tse-governador-rs-municipio.csv")
OBRIG = ["turno", "uf", "cod_municipio", "municipio", "cargo", "numero", "votos"]


def ler_ano(ano: int) -> pd.DataFrame:
    with zipfile.ZipFile(RAW / f"votacao_candidato_munzona_{ano}.zip") as zf:
        nome = [n for n in zf.namelist() if n.upper().endswith(("_RS.CSV", "_RS.TXT"))][0]
        with zf.open(nome) as f:
            cab = pd.read_csv(f, sep=";", encoding="latin-1", nrows=0, dtype=str)
        mapa = mapear_colunas(list(cab.columns), ALIASES_CANDIDATO, OBRIG)
        inverso, partes = {v: k for k, v in mapa.items()}, []
        with zf.open(nome) as f:
            for ch in pd.read_csv(f, sep=";", encoding="latin-1", dtype=str, usecols=list(mapa.values()), chunksize=CHUNK):
                ch = ch.rename(columns=inverso)
                ch = ch[ch["cargo"].map(normalizar_texto) == "GOVERNADOR"]
                if len(ch):
                    partes.append(ch)
    df = pd.concat(partes, ignore_index=True)
    df["votos"] = pd.to_numeric(df["votos"], errors="coerce").fillna(0)
    df["turno"] = df["turno"].astype(int)
    df["cod_municipio"] = df["cod_municipio"].str.strip().str.zfill(5)
    for c in ("municipio", "nome", "partido"):
        df[c] = df[c].astype(str).str.strip() if c in df else ""
    g = df.groupby(["turno", "cod_municipio", "municipio", "numero", "nome", "partido"], as_index=False)["votos"].sum()
    g.insert(0, "ano", ano)
    return g


if __name__ == "__main__":
    out = pd.concat([ler_ano(a) for a in range(2002, 2023, 4)], ignore_index=True)
    out.to_csv(SAIDA, index=False)
    res = out.groupby(["ano", "turno", "nome", "partido"], as_index=False).votos.sum()
    res["pct_validos"] = 100 * res.votos / res.groupby(["ano", "turno"]).votos.transform("sum")
    print(SAIDA, len(out), "linhas")
    for (a, t), g in res.groupby(["ano", "turno"]):
        print(a, t, "|", "; ".join(f"{r.nome} ({r.partido}) {r.pct_validos:.1f}" for r in g.sort_values("votos", ascending=False).head(5).itertuples()))

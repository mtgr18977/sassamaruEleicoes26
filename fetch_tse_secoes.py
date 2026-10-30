"""Votação para presidente por SEÇÃO eleitoral (boletim de urna) em 2026, 1º e 2º turnos.

  python fetch_tse_secoes.py [votacao_secao_2026_BR.zip]
Lê o arquivo de dados abertos do TSE (cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_BR.zip; ~240 MB, 1,5 GB de CSV, gerado em 26/10/2026),
confere os totais com o resultado oficial e grava:
  datasets/tse-presidente-secao-2026.csv.gz  uma linha por seção (uf, município, zona, seção, local) com Lula, Flávio, outros, brancos e nulos nos dois turnos (NÃO vai para o git: ~25 MB)
  datasets/tse-presidente-zona-2026.csv      agregado por (município, zona): vai para o git
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

ZIP = Path(sys.argv[1] if len(sys.argv) > 1 else "datasets/tse_raw/votacao_secao_2026_BR.zip")
LULA, FLAVIO = 13, 22
CHAVE = ["uf", "cod_municipio", "municipio", "zona", "secao", "local", "endereco"]


def ler() -> pd.DataFrame:
    partes = []
    with zipfile.ZipFile(ZIP) as z:
        nome = [n for n in z.namelist() if n.endswith(".csv")][0]
        cols = ["NR_TURNO", "DS_CARGO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_VOTAVEL", "QT_VOTOS", "NM_LOCAL_VOTACAO", "DS_LOCAL_VOTACAO_ENDERECO"]
        for ch in pd.read_csv(z.open(nome), sep=";", encoding="latin-1", dtype=str, usecols=cols, chunksize=1_500_000):
            ch = ch[ch.DS_CARGO == "Presidente"]
            ch = ch.rename(columns={"NR_TURNO": "turno", "SG_UF": "uf", "CD_MUNICIPIO": "cod_municipio", "NM_MUNICIPIO": "municipio", "NR_ZONA": "zona", "NR_SECAO": "secao",
                                    "NM_LOCAL_VOTACAO": "local", "DS_LOCAL_VOTACAO_ENDERECO": "endereco"})
            v = ch.NR_VOTAVEL.astype(int)
            ch["col"] = v.map({LULA: "lula", FLAVIO: "flavio", 95: "branco", 96: "nulo"}).fillna("outros")
            ch["votos"] = ch.QT_VOTOS.astype(int)
            partes.append(ch.groupby(CHAVE[:5] + ["turno", "col"], as_index=False).agg(votos=("votos", "sum"), local=("local", "first"), endereco=("endereco", "first")))
    d = pd.concat(partes).groupby(CHAVE[:5] + ["turno", "col"], as_index=False).agg(votos=("votos", "sum"), local=("local", "first"), endereco=("endereco", "first"))
    loc = d.drop_duplicates(CHAVE[:5])[CHAVE]
    w = d.pivot_table(index=CHAVE[:5], columns=["turno", "col"], values="votos", aggfunc="sum", fill_value=0)
    w.columns = [f"{c}_t{t}" for t, c in w.columns]
    return w.reset_index().merge(loc, on=CHAVE[:5], how="left")


if __name__ == "__main__":
    s = ler()
    for t in (1, 2):
        s[f"validos_t{t}"] = s[f"lula_t{t}"] + s[f"flavio_t{t}"] + (s[f"outros_t{t}"] if t == 1 else 0)
    print(len(s), "seções;", "Lula 2T", int(s.lula_t2.sum()), "Flávio 2T", int(s.flavio_t2.sum()), "Lula 1T", int(s.lula_t1.sum()), "Flávio 1T", int(s.flavio_t1.sum()))
    assert s.lula_t2.sum() == 64_256_232 and s.flavio_t2.sum() == 59_826_041 and s.lula_t1.sum() == 53_879_538 and s.flavio_t1.sum() == 56_104_503
    s.to_csv("datasets/tse-presidente-secao-2026.csv.gz", index=False)
    z = s.groupby(["uf", "cod_municipio", "municipio", "zona"], as_index=False)[[c for c in s.columns if c.endswith(("_t1", "_t2"))]].sum()
    z["secoes"] = s.groupby(["uf", "cod_municipio", "municipio", "zona"]).size().values
    z.to_csv("datasets/tse-presidente-zona-2026.csv", index=False)
    print(len(z), "zonas")

"""Presidente e governador em Porto Alegre, por zona eleitoral, 2018, 2022 e 2026 (1º e 2º turnos).

  python fetch_tse_poa.py
Lê datasets/tse_raw/votacao_candidato_munzona_AAAA.zip (dados abertos do TSE; os mesmos zips do fetch_tse.py): o presidente está no arquivo *_BR.csv e o governador no *_RS.csv.
Sai: datasets/tse-portoalegre-zona.csv (ano, turno, cargo, zona, candidato, partido, votos nominais). Em 2026 o governador só teve 1º turno (Zucco foi eleito)."""
import zipfile
from pathlib import Path

import pandas as pd

COLS = ["NR_TURNO", "DS_CARGO", "NM_MUNICIPIO", "NR_ZONA", "NM_URNA_CANDIDATO", "SG_PARTIDO", "QT_VOTOS_NOMINAIS"]


def main() -> None:
    partes = []
    for ano in (2018, 2022, 2026):
        with zipfile.ZipFile(f"datasets/tse_raw/votacao_candidato_munzona_{ano}.zip") as z:
            for nome in z.namelist():
                if not nome.upper().endswith(("_BR.CSV", "_RS.CSV")):
                    continue
                for ch in pd.read_csv(z.open(nome), sep=";", encoding="latin-1", dtype=str, usecols=COLS, chunksize=500_000):
                    ch = ch[(ch.NM_MUNICIPIO.str.upper() == "PORTO ALEGRE") & ch.DS_CARGO.str.upper().isin(["PRESIDENTE", "GOVERNADOR"])]
                    if len(ch):
                        partes.append(ch.assign(ano=ano))
    d = pd.concat(partes).rename(columns={"NR_TURNO": "turno", "DS_CARGO": "cargo", "NR_ZONA": "zona", "NM_URNA_CANDIDATO": "candidato", "SG_PARTIDO": "partido"})
    d["votos"] = d.QT_VOTOS_NOMINAIS.astype(int)
    d["cargo"] = d.cargo.str.title()
    g = d.groupby(["ano", "turno", "cargo", "zona", "candidato", "partido"], as_index=False).votos.sum()
    g["turno"], g["zona"] = g.turno.astype(int), g.zona.astype(int)
    g.sort_values(["ano", "turno", "cargo", "zona", "votos"], ascending=[True, True, True, True, False]).to_csv("datasets/tse-portoalegre-zona.csv", index=False)
    print(len(g), "linhas;", g.groupby(["ano", "turno", "cargo"]).votos.sum().to_dict())


if __name__ == "__main__":
    main()

"""Valida a distribuição regional do modelo contra o cruzamento por região da Datafolha (22-23/09/2026).

Compara Lula/(Lula+Flávio) por região: modelo (base 2022 + total nacional das pesquisas) × pesquisa.
Não é independente do total nacional (a Datafolha entra nas pesquisas), mas testa a estrutura regional.
1º turno usa a projeção atual (modelos/projecao-1turno*); 2º turno, o Monte Carlo atual.
"""
import numpy as np
import pandas as pd
from nivel2 import REGIAO

D = "datasets/"
REG4 = {"SE": "Sudeste", "S": "Sul", "NE": "Nordeste", "N": "Centro-Oeste/Norte", "CO": "Centro-Oeste/Norte"}


def comparar():
    pesos = pd.read_csv(D + "tse-presidente-uf.csv").query("ano == 2022 and turno == 1 and uf != 'VT' and uf != 'ZZ'").set_index("uf").validos
    df = pd.read_csv(D + "datafolha-regioes-2026-09-22.csv")
    df["datafolha"] = 100 * df.lula / (df.lula + df.flavio)
    p1 = pd.read_csv("modelos/projecao-1turno-uf-pesquisas.csv").set_index("uf").drop("ZZ", errors="ignore")
    p2 = pd.read_csv("modelos/previsao-uf-turno2.csv").set_index("uf").drop("ZZ", errors="ignore")
    saida = []
    for turno, (p, num, den) in {1: (p1, "lula", ("lula", "flavio")), 2: (p2, "mediana", None)}.items():
        reg = p.index.map(lambda u: REG4[REGIAO[u]]); w = pesos.reindex(p.index)
        for r, g in p.groupby(reg):
            ww = w[g.index]
            modelo = 100 * np.average(g.lula, weights=ww) / (np.average(g.lula, weights=ww) + np.average(g.flavio, weights=ww)) if turno == 1 \
                else np.average(g.mediana, weights=ww)
            d = df[(df.turno == turno) & (df.recorte == r)].iloc[0]
            saida.append(dict(turno=turno, regiao=r, modelo=round(modelo, 1), datafolha=round(d.datafolha, 1), dif=round(modelo - d.datafolha, 1), me=int(d.margem_erro_pp)))
    return saida


if __name__ == "__main__":
    print(pd.DataFrame(comparar()).to_string(index=False))

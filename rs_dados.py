"""Governador do RS: blocos, unidades regionais e tabelas históricas (2002–2022) a partir dos CSVs de datasets/.

Blocos (por partido; pressuposto documentado): E = esquerda (PT, PDT, PSOL, PSB, PV, PSTU, PCO, PCB),
C = centro (PMDB/MDB, PSDB, PPS), D = direita (PP/PPB, PL, PSC, NOVO, PRTB, PRP e demais).
Unidades: Porto Alegre, Metropolitana sem a capital e as outras 6 mesorregiões do IBGE.
"""
import pandas as pd

D = "datasets/"
ESQ = {"PT", "PDT", "PSOL", "PSB", "PV", "PSTU", "PCO", "PCB"}
CEN = {"PMDB", "MDB", "PSDB", "PPS"}
NOME_UNIDADE = {"Porto Alegre": "Porto Alegre", "Metropolitana (sem POA)": "Grande POA (sem capital)", "Nordeste Rio-grandense": "Nordeste (Serra)",
                "Noroeste Rio-grandense": "Noroeste", "Centro Oriental Rio-grandense": "Centro Oriental", "Centro Ocidental Rio-grandense": "Centro Ocidental",
                "Sudeste Rio-grandense": "Sudeste", "Sudoeste Rio-grandense": "Sudoeste"}


def bloco(partido: str) -> str:
    return "E" if partido in ESQ else "C" if partido in CEN else "D"


def carregar():
    m = pd.read_csv(D + "tse-governador-rs-municipio.csv", dtype={"cod_municipio": str})
    r = pd.read_csv(D + "rs-municipios-regioes.csv", dtype={"cod_municipio": str})
    r["unidade"] = r.meso
    r.loc[r.municipio == "PORTO ALEGRE", "unidade"] = "Porto Alegre"
    r.loc[(r.meso == "Metropolitana de Porto Alegre") & (r.municipio != "PORTO ALEGRE"), "unidade"] = "Metropolitana (sem POA)"
    m = m.merge(r[["cod_municipio", "unidade", "meso"]], on="cod_municipio")
    m["bloco"] = m.partido.map(bloco)
    m["unidade_nome"] = m.unidade.map(NOME_UNIDADE)
    return m


def blocos_por_unidade(m, turno=1):
    """DataFrame (ano, unidade_nome, E, C, D, validos) com % por bloco no 1º turno (ou %vencedor no 2º, via candidatos)."""
    g = m[m.turno == turno].groupby(["ano", "unidade_nome", "bloco"]).votos.sum().unstack("bloco").fillna(0)
    g["validos"] = g.sum(axis=1)
    for b in "ECD":
        g[b] = g[b] / g.validos
    return g.reset_index()


if __name__ == "__main__":
    m = carregar()
    pd.options.display.float_format = "{:.3f}".format
    est = m[m.turno == 1].groupby(["ano", "bloco"]).votos.sum().unstack().pipe(lambda d: d.div(d.sum(axis=1), axis=0))
    print("Estado, 1º turno, % por bloco\n", (100 * est).round(1).to_string())
    u = blocos_por_unidade(m)
    print("\n2022 por unidade\n", u[u.ano == 2022].round(3).to_string(index=False))
    print("\nunidades:", u.unidade_nome.nunique(), "| municípios por unidade:", m[m.ano == 2022].drop_duplicates("cod_municipio").groupby("unidade_nome").size().to_dict())

"""Simulação: e se o RS elegesse deputados só pelos mais votados (distritão), sem quociente, partidos, federações ou sobras?

  python distritao_rs.py
Para cada eleição (2018, 2022, 2026) e cada cargo (Deputado Federal: 31 cadeiras; Deputado Estadual: 55), pega os votos nominais VÁLIDOS de cada candidato (soma das zonas, arquivo *_RS.csv de
datasets/tse_raw/votacao_candidato_munzona_AAAA.zip, dados abertos do TSE) e elege os N mais votados do estado, sem olhar partido. Compara com os eleitos de verdade (DS_SIT_TOT_TURNO:
"ELEITO POR QP" ou "POR MÉDIA"). Não muda o comportamento do eleitor nem as candidaturas: é a mesma votação, lida de outro jeito (a conta tem esse limite, e a página diz).
Sai: modelos/distritao-rs.json."""
import json
import zipfile
from collections import Counter

import numpy as np
import pandas as pd

from rs_bancada import ESQ, CEN, RENOME

CARGOS = {"Deputado Federal": ("DF", 31), "Deputado Estadual": ("DE", 55)}
ANOS = (2018, 2022, 2026)
COLS = ["DS_CARGO", "SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO", "NM_FEDERACAO", "NM_COLIGACAO", "QT_VOTOS_NOMINAIS_VALIDOS", "DS_SIT_TOT_TURNO", "NM_TIPO_DESTINACAO_VOTOS"]
r1 = lambda x: round(float(x), 1)
bloco = lambda p: "E" if p in ESQ else "C" if p in CEN else "D"
BNOME = {"E": "Esquerda", "C": "Centro", "D": "Direita e demais"}


def lista_de(r) -> str:
    """Unidade de disputa das cadeiras: federação (2022/2026), coligação (2018) ou o partido sozinho."""
    for c in ("NM_FEDERACAO", "NM_COLIGACAO"):
        v = r[c]
        if isinstance(v, str) and v not in ("#NULO", "#NE", "PARTIDO ISOLADO", ""):
            return v
    return r["SG_PARTIDO"]


def candidatos(ano: int) -> pd.DataFrame:
    with zipfile.ZipFile(f"datasets/tse_raw/votacao_candidato_munzona_{ano}.zip") as z:
        nome = [n for n in z.namelist() if n.endswith("_RS.csv")][0]
        d = pd.read_csv(z.open(nome), sep=";", encoding="latin-1", dtype=str, usecols=lambda c: c in COLS)
    d = d[d.DS_CARGO.isin(CARGOS)].copy()
    d["v"] = d.QT_VOTOS_NOMINAIS_VALIDOS.astype(int)
    g = d.groupby(["DS_CARGO", "SQ_CANDIDATO"], as_index=False).agg(nome=("NM_URNA_CANDIDATO", "first"), partido=("SG_PARTIDO", "first"), fed=("NM_FEDERACAO", "first"), col=("NM_COLIGACAO", "first"),
                                                                    votos=("v", "sum"), sit=("DS_SIT_TOT_TURNO", "first"))
    g["partido"] = g.partido.map(lambda p: RENOME.get(p, p)).replace({"PCDOB": "PCdoB"})
    g["lista"] = [lista_de({"NM_FEDERACAO": f, "NM_COLIGACAO": c, "SG_PARTIDO": p}) for f, c, p in zip(g.fed, g.col, g.partido)]
    g["eleito"] = g.sit.isin(["ELEITO POR QP", "ELEITO POR MÉDIA"])
    return g


def votos_validos_totais(ano: int, cargo: str) -> int | None:
    """Votos válidos (nominais + legenda) da eleição: só o arquivo de detalhe de 2026 está em datasets/tse_raw; antes, soma das listas de tse-legislativo-rs-listas.csv."""
    if ano == 2026:
        with zipfile.ZipFile("datasets/tse_raw/detalhe_votacao_munzona_2026.zip") as z:
            d = pd.read_csv(z.open("detalhe_votacao_munzona_2026_RS.csv"), sep=";", encoding="latin-1", dtype=str, usecols=["DS_CARGO", "QT_TOTAL_VOTOS_VALIDOS"])
        return int(d[d.DS_CARGO == cargo].QT_TOTAL_VOTOS_VALIDOS.astype(int).sum())
    ls = pd.read_csv("datasets/tse-legislativo-rs-listas.csv")
    return int(ls[(ls.ano == ano) & (ls.cargo == CARGOS[cargo][0])].votos.sum())


def enp(cont) -> float:
    """Número efetivo de partidos pelas cadeiras: 1 / soma dos quadrados das parcelas."""
    t = sum(cont.values())
    return round(1 / sum((v / t) ** 2 for v in cont.values()), 2)


def simular(g: pd.DataFrame, cargo: str, ano: int) -> dict:
    sig, n = CARGOS[cargo]
    c = g[g.DS_CARGO == cargo].sort_values(["votos", "SQ_CANDIDATO"], ascending=[False, True]).reset_index(drop=True)
    c["pos"] = np.arange(1, len(c) + 1)
    c["dist"] = c.pos <= n
    assert int(c.eleito.sum()) == n, (ano, cargo, int(c.eleito.sum()))
    vv = votos_validos_totais(ano, cargo)
    qe = vv / n
    nominais = int(c.votos.sum())
    lin = lambda r: dict(nome=r.nome.title(), partido=r.partido, votos=int(r.votos), pos=int(r.pos), lista=r.lista)
    so_atual = c[c.eleito & ~c.dist]                     # eleitos de verdade que não estariam entre os N mais votados
    so_dist = c[~c.eleito & c.dist]                      # entre os N mais votados mas sem cadeira
    # por partido
    pa, pd_ = Counter(c[c.eleito].partido), Counter(c[c.dist].partido)
    partidos = [dict(partido=p, atual=pa.get(p, 0), distritao=pd_.get(p, 0), dif=pd_.get(p, 0) - pa.get(p, 0)) for p in sorted(set(pa) | set(pd_), key=lambda p: (-(pa.get(p, 0) + pd_.get(p, 0)), p))]
    blocos = {k: dict(atual=int(sum(v for p, v in pa.items() if bloco(p) == k)), distritao=int(sum(v for p, v in pd_.items() if bloco(p) == k))) for k in "ECD"}
    # por lista (federação, coligação ou partido): onde estão os "puxados"
    por_lista = []
    for l, x in c.groupby("lista"):
        a, d_ = int(x.eleito.sum()), int(x.dist.sum())
        if a or d_:
            top = x.iloc[0]
            por_lista.append(dict(lista=l, atual=a, distritao=d_, votos_lista=int(x.votos.sum()), campeao=top.nome.title(), votos_campeao=int(top.votos), pos_campeao=int(top.pos),
                                  parte_do_campeao=r1(100 * top.votos / x.votos.sum()), eleitos_abaixo_do_corte=int((x.eleito & ~x.dist).sum())))
    por_lista.sort(key=lambda r: (-(r["atual"] + r["distritao"]), r["lista"]))
    eleitos_atual = c[c.eleito]; eleitos_dist = c[c.dist]
    corte = int(c.votos.iloc[n - 1])
    return dict(sigla=sig, cadeiras=n, candidatos=int(len(c)), votos_nominais=nominais, votos_validos=vv, legenda_pct=r1(100 * (vv - nominais) / vv), quociente=int(qe),
                corte_distritao=corte, menor_eleito_atual=int(eleitos_atual.votos.min()), maior_nao_eleito_atual=int(c[~c.eleito].votos.max()),
                eleitos_abaixo_do_quociente=int((eleitos_atual.votos < qe).sum()), eleitos_acima_do_quociente=int((eleitos_atual.votos >= qe).sum()),
                mediana_votos_atual=int(eleitos_atual.votos.median()), mediana_votos_distritao=int(eleitos_dist.votos.median()),
                iguais=int((c.eleito & c.dist).sum()), trocas=int(len(so_atual)),
                so_atual=[lin(r) for _, r in so_atual.sort_values("votos", ascending=False).iterrows()], so_distritao=[lin(r) for _, r in so_dist.sort_values("votos", ascending=False).iterrows()],
                partidos=partidos, blocos=blocos, listas=por_lista[:14], top10=[lin(r) | dict(eleito=bool(r.eleito)) for _, r in c.head(10).iterrows()],
                n_partidos_atual=len(pa), n_partidos_distritao=len(pd_), enp_atual=enp(pa), enp_distritao=enp(pd_),
                puxadores=[dict(nome=r.nome.title(), partido=r.partido, votos=int(r.votos), em_quocientes=round(float(r.votos / qe), 2), excesso=round(float(max(r.votos - qe, 0) / qe), 2), eleito=bool(r.eleito),
                                companheiros_eleitos=int(((c.lista == r.lista) & c.eleito).sum()) - int(r.eleito), companheiros_abaixo_do_corte=int(((c.lista == r.lista) & c.eleito & ~c.dist).sum()))
                           for _, r in c[c.votos >= 0.5 * qe].iterrows()],
                excesso_total=round(float(((c.votos - qe).clip(lower=0) / qe).sum()), 2))


def main() -> None:
    saida = {}
    for ano in ANOS:
        g = candidatos(ano)
        saida[str(ano)] = {CARGOS[c][0]: simular(g, c, ano) for c in CARGOS}
        for sig in ("DF", "DE"):
            s = saida[str(ano)][sig]
            print(ano, sig, "iguais", s["iguais"], "de", s["cadeiras"], "| corte", s["corte_distritao"], "| QE", s["quociente"], "| eleitos abaixo do QE", s["eleitos_abaixo_do_quociente"], "| blocos", s["blocos"])
    json.dump(saida, open("modelos/distritao-rs.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()

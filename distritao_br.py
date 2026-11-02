"""Distritão no Brasil: e se cada UF elegesse seus deputados (federais e estaduais/distritais) só pelos mais votados?

  python distritao_br.py
Para cada UF, eleição (2018, 2022, 2026) e cargo, soma os votos nominais VÁLIDOS de cada candidato (arquivo *_UF.csv de datasets/tse_raw/votacao_candidato_munzona_AAAA.zip, dados abertos do TSE),
elege os N mais votados da UF (N = número de eleitos de verdade na UF, pela situação ELEITO POR QP/MÉDIA do próprio TSE; a soma tem de dar 513 na Câmara) e compara com os eleitos de verdade.
Mesma votação nos dois sistemas: não modela mudança de candidaturas nem de voto. Sai: modelos/distritao-br.json (a página: distritao-brasil.html)."""
import json
import zipfile
from collections import Counter

import numpy as np
import pandas as pd

from distritao_rs import bloco, enp, r1
from rs_bancada import RENOME

CARGOS = {"Deputado Federal": "DF", "Deputado Estadual": "DE", "Deputado Distrital": "DE"}
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]
COLS = ["DS_CARGO", "SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO", "NM_FEDERACAO", "NM_COLIGACAO", "QT_VOTOS_NOMINAIS_VALIDOS", "DS_SIT_TOT_TURNO"]
LIMPA = {"PCDOB": "PCdoB", "PSL": "UNIÃO", "PRD": "PRD"}
ANOS = (2018, 2022, 2026)
MAIORIA = 257


def lista_de(f, c, p) -> str:
    for v in (f, c):
        if isinstance(v, str) and not v.startswith("#") and v not in ("PARTIDO ISOLADO", "FEDERAÇÃO", ""):
            return v
    return p


def candidatos(ano: int) -> pd.DataFrame:
    partes = []
    with zipfile.ZipFile(f"datasets/tse_raw/votacao_candidato_munzona_{ano}.zip") as z:
        for uf in UFS:
            d = pd.read_csv(z.open(f"votacao_candidato_munzona_{ano}_{uf}.csv"), sep=";", encoding="latin-1", dtype=str, usecols=lambda c: c in COLS)
            d = d[d.DS_CARGO.isin(CARGOS)].copy()
            d["v"] = d.QT_VOTOS_NOMINAIS_VALIDOS.astype(int)
            g = d.groupby(["DS_CARGO", "SQ_CANDIDATO"], as_index=False).agg(nome=("NM_URNA_CANDIDATO", "first"), partido=("SG_PARTIDO", "first"), fed=("NM_FEDERACAO", "first"), col=("NM_COLIGACAO", "first"),
                                                                            votos=("v", "sum"), sit=("DS_SIT_TOT_TURNO", "first"))
            g["uf"], g["cargo"] = uf, g.DS_CARGO.map(CARGOS)
            partes.append(g)
    g = pd.concat(partes, ignore_index=True)
    g["partido"] = g.partido.map(lambda p: RENOME.get(p, p)).map(lambda p: LIMPA.get(p, p))
    g["lista"] = [lista_de(f, c, p) for f, c, p in zip(g.fed, g.col, g.partido)]
    g["eleito"] = g.sit.isin(["ELEITO POR QP", "ELEITO POR MÉDIA"])
    return g


def qe_2026() -> dict:
    """Quociente eleitoral por (UF, cargo) em 2026: votos válidos (nominais + legenda) ÷ cadeiras, do arquivo de detalhe."""
    out = {}
    with zipfile.ZipFile("datasets/tse_raw/detalhe_votacao_munzona_2026.zip") as z:
        for uf in UFS:
            d = pd.read_csv(z.open(f"detalhe_votacao_munzona_2026_{uf}.csv"), sep=";", encoding="latin-1", dtype=str, usecols=["DS_CARGO", "QT_TOTAL_VOTOS_VALIDOS"])
            for c, s in d.groupby("DS_CARGO").QT_TOTAL_VOTOS_VALIDOS.apply(lambda x: x.astype(int).sum()).items():
                if c in CARGOS:
                    out[(uf, CARGOS[c])] = int(s)
    return out


def simular_uf(g: pd.DataFrame) -> pd.DataFrame:
    """Marca, em cada UF e cargo, os N mais votados (N = nº de eleitos de verdade)."""
    g = g.sort_values(["uf", "cargo", "votos", "SQ_CANDIDATO"], ascending=[True, True, False, True]).copy()
    g["pos"] = g.groupby(["uf", "cargo"]).cumcount() + 1
    n = g.groupby(["uf", "cargo"]).eleito.transform("sum")
    g["n"], g["dist"] = n, g.pos <= n
    return g


def resumo(g: pd.DataFrame, cargo: str, ano: int, qe: dict | None) -> dict:
    c = g[g.cargo == cargo]
    seats = int(c.eleito.sum())
    pa, pd_ = Counter(c[c.eleito].partido), Counter(c[c.dist].partido)
    vt = c.groupby("partido").votos.sum()
    partidos = [dict(partido=p, atual=pa.get(p, 0), distritao=pd_.get(p, 0), dif=pd_.get(p, 0) - pa.get(p, 0), votos_pct=r1(100 * vt.get(p, 0) / vt.sum())) for p in sorted(set(pa) | set(pd_), key=lambda p: (-max(pa.get(p, 0), pd_.get(p, 0)), p))]
    blocos = {k: dict(atual=int(sum(v for p, v in pa.items() if bloco(p) == k)), distritao=int(sum(v for p, v in pd_.items() if bloco(p) == k))) for k in "ECD"}
    por_uf = []
    for uf, x in c.groupby("uf"):
        a, d_ = Counter(x[x.eleito].partido), Counter(x[x.dist].partido)
        por_uf.append(dict(uf=uf, cadeiras=int(x.eleito.sum()), trocas=int((x.eleito & ~x.dist).sum()), pl_atual=a.get("PL", 0), pl_dist=d_.get("PL", 0),
                           e_atual=int(sum(v for p, v in a.items() if bloco(p) == "E")), e_dist=int(sum(v for p, v in d_.items() if bloco(p) == "E")),
                           d_atual=int(sum(v for p, v in a.items() if bloco(p) == "D")), d_dist=int(sum(v for p, v in d_.items() if bloco(p) == "D")),
                           corte=int(x[x.dist].votos.min()), menor_eleito=int(x[x.eleito].votos.min()), maior_fora=int(x[~x.eleito].votos.max())))
    lin = lambda r: dict(uf=r.uf, nome=r.nome.title(), partido=r.partido, votos=int(r.votos), pos=int(r.pos))
    sai, entra = c[c.eleito & ~c.dist], c[~c.eleito & c.dist]
    out = dict(cadeiras=seats, trocas=int(len(sai)), iguais=seats - int(len(sai)), partidos=partidos, blocos=blocos, por_uf=por_uf, enp_atual=enp(pa), enp_distritao=enp(pd_),
               n_partidos_atual=len(pa), n_partidos_distritao=len(pd_), ufs_com_troca=int(sum(1 for u in por_uf if u["trocas"])),
               maiores_que_saem=[lin(r) for _, r in sai.sort_values("votos", ascending=False).head(12).iterrows()], maiores_que_entram=[lin(r) for _, r in entra.sort_values("votos", ascending=False).head(12).iterrows()],
               pl=dict(atual=pa.get("PL", 0), distritao=pd_.get("PL", 0)))
    if qe is not None:                                           # puxadores (só 2026, que tem o detalhe com votos de legenda)
        c = c.assign(qe=[qe[(u, cargo)] / n for u, n in zip(c.uf, c.n)])
        c["excesso"] = ((c.votos - c.qe).clip(lower=0) / c.qe)
        p = c[c.votos >= c.qe]
        out["puxadores"] = dict(n=int(len(p)), excesso_total=round(float(c.excesso.sum()), 1), pl_excesso=round(float(c[c.partido == "PL"].excesso.sum()), 1),
                                topo=[dict(uf=r.uf, nome=r.nome.title(), partido=r.partido, votos=int(r.votos), em_quocientes=round(float(r.votos / r.qe), 2),
                                           colegas_abaixo_do_corte=int(((c.uf == r.uf) & (c.lista == r.lista) & c.eleito & ~c.dist).sum()))
                                      for _, r in p.sort_values("excesso", ascending=False).head(12).iterrows()])
    return out


def gallagher(c: pd.DataFrame, col: str) -> float:
    """Índice de Gallagher entre a parcela de votos nominais de cada partido (nacional) e a parcela de cadeiras: quanto maior, menos proporcional (em p.p.)."""
    v = c.groupby("partido").votos.sum()
    v = 100 * v / v.sum()
    s = 100 * c[c[col]].groupby("partido").size().reindex(v.index).fillna(0) / c[col].sum()
    return float(np.sqrt(0.5 * ((v - s) ** 2).sum()))


def analise(c: pd.DataFrame, cargo: str, qe: dict | None) -> dict:
    """Mecanismos por trás das trocas: quem sai e quem entra, quanto vem de puxadores, concentração de votos por partido, proporcionalidade, votos que não elegem e tamanho da UF."""
    c = c.copy()
    c["eleito_dist"] = c.dist
    tot = float(c.votos.sum())
    sai, entra = c[c.eleito & ~c.dist], c[~c.eleito & c.dist]
    out = dict(sai_n=int(len(sai)), entra_n=int(len(entra)), votos_medianos_sai=int(sai.votos.median()), votos_medianos_entra=int(entra.votos.median()),
               razao_media_entra_sai=round(float(entra.votos.mean() / sai.votos.mean()), 2), gallagher_atual=round(gallagher(c, "eleito"), 2), gallagher_distritao=round(gallagher(c, "dist"), 2))
    # votos que não elegem ninguém
    lista_sem = c.groupby(["uf", "lista"]).eleito.transform("sum") == 0
    out["votos_sem_cadeira"] = dict(lista_sem_cadeira_pct=r1(100 * c[lista_sem].votos.sum() / tot), nao_eleitos_atual_pct=r1(100 * c[~c.eleito].votos.sum() / tot), fora_dos_n_distritao_pct=r1(100 * c[~c.dist].votos.sum() / tot))
    # por tamanho da UF
    faixas = [(0, 10, "até 10 cadeiras"), (11, 20, "11 a 20"), (21, 40, "21 a 40"), (41, 999, "mais de 40")] if cargo == "DF" else [(0, 30, "até 30 cadeiras"), (31, 45, "31 a 45"), (46, 70, "46 a 70"), (71, 999, "mais de 70")]
    mag = []
    for lo, hi, nome in faixas:
        x = c[(c.n >= lo) & (c.n <= hi)]
        if len(x):
            mag.append(dict(faixa=nome, ufs=int(x.uf.nunique()), cadeiras=int(x.eleito.sum()), trocas=int((x.eleito & ~x.dist).sum()), pl_atual=int((x.eleito & (x.partido == "PL")).sum()), pl_dist=int((x.dist & (x.partido == "PL")).sum())))
    out["por_tamanho"] = mag
    if qe is not None:
        c["qe"] = [qe[(u, cargo)] / n for u, n in zip(c.uf, c.n)]
        estrela = set(map(tuple, c[c.votos >= c.qe][["uf", "lista"]].values))
        sai = sai.assign(puxado=[(u, l) in estrela for u, l in zip(sai.uf, sai.lista)])
        por = []
        for p, x in sai.groupby("partido"):
            e = entra[entra.partido == p]
            por.append(dict(partido=p, sai=int(len(x)), sai_com_puxador_na_lista=int(x.puxado.sum()), entra=int(len(e))))
        out["mecanismos"] = dict(sai_com_puxador=int(sai.puxado.sum()), sai_sem_puxador=int((~sai.puxado).sum()), por_partido=sorted(por, key=lambda r: -(r["sai"] + r["entra"]))[:12],
                                 pl=next((r for r in por if r["partido"] == "PL"), None))
        # concentração: parcela dos votos do partido que são "excesso de estrela" (votos acima de 1 quociente)
        c["exc"] = (c.votos - c.qe).clip(lower=0)
        pa, pdn = Counter(c[c.eleito].partido), Counter(c[c.dist].partido)
        linhas = []
        for p, x in c.groupby("partido"):
            if max(pa.get(p, 0), pdn.get(p, 0)) >= 8:
                linhas.append(dict(partido=p, votos_pct=r1(100 * x.votos.sum() / tot), estrelas_pct=r1(100 * x.exc.sum() / x.votos.sum()), atual=pa.get(p, 0), distritao=pdn.get(p, 0), var_pct=r1(100 * (pdn.get(p, 0) - pa.get(p, 0)) / max(pa.get(p, 0), 1))))
        a, b = np.array([l["estrelas_pct"] for l in linhas]), np.array([l["var_pct"] for l in linhas])
        rk = lambda v: pd.Series(v).rank().values
        if len(linhas) >= 5:      # com poucos partidos (uma UF só) a correlação não faz sentido
          out["concentracao"] = dict(partidos=sorted(linhas, key=lambda l: -l["estrelas_pct"]), corr=round(float(np.corrcoef(a, b)[0, 1]), 2), corr_spearman=round(float(np.corrcoef(rk(a), rk(b))[0, 1]), 2), n=len(linhas))
    return out


def main() -> None:
    saida = {}
    qe = qe_2026()
    for ano in ANOS:
        g = simular_uf(candidatos(ano))
        saida[str(ano)] = {}
        for cargo in ("DF", "DE"):
            r = resumo(g, cargo, ano, qe if ano == 2026 else None)
            r["analise"] = analise(g[g.cargo == cargo], cargo, qe if ano == 2026 else None)
            if ano == 2026:
                r["analise_rs"] = analise(g[(g.cargo == cargo) & (g.uf == "RS")], cargo, qe)
            saida[str(ano)][cargo] = r
            print(ano, cargo, "cadeiras", r["cadeiras"], "trocas", r["trocas"], "| PL", r["pl"], "| blocos", r["blocos"], "| ENP", r["enp_atual"], r["enp_distritao"])
        assert saida[str(ano)]["DF"]["cadeiras"] == 513, ano
    json.dump(saida, open("modelos/distritao-br.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()

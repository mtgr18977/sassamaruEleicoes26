"""Onde Lula virou e onde Flávio virou ou se manteve: 1º × 2º turno de 2026 por seção, zona, município e UF.

  python analisar_secoes_2026.py
Entrada: datasets/tse-presidente-secao-2026.csv.gz (fetch_tse_secoes.py; boletins de urna) e datasets/tse-presidente-municipio.csv (2022, para comparar).
Saída: modelos/secoes-2026.json. A "% de Lula" é sempre Lula/(Lula+Flávio), nos dois turnos (no 1º, os outros candidatos ficam de fora), para poder comparar os turnos.
"Virou" = o candidato perdeu naquela unidade no 1º turno e ganhou no 2º. A estimativa de para onde foram os votos dos outros candidatos é regressão ecológica (por seção): é indício, não prova."""
import json

import numpy as np
import pandas as pd
from scipy.optimize import nnls

REGIAO = {"N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul"}
UF_REG = {**dict.fromkeys(["RR", "AP", "AC", "AM", "PA", "RO", "TO"], "N"), **dict.fromkeys(["MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA"], "NE"),
          **dict.fromkeys(["MT", "MS", "GO", "DF"], "CO"), **dict.fromkeys(["SP", "RJ", "MG", "ES"], "SE"), **dict.fromkeys(["PR", "SC", "RS"], "S")}
r1 = lambda x: round(float(x), 1)


def carregar() -> pd.DataFrame:
    s = pd.read_csv("datasets/tse-presidente-secao-2026.csv.gz", dtype={"cod_municipio": str, "zona": str, "secao": str})
    s = s[s.uf != "ZZ"].copy()
    s["outros_t2"] = 0
    s["v1"], s["v2"] = s.lula_t1 + s.flavio_t1, s.lula_t2 + s.flavio_t2
    s["bn1"], s["bn2"] = s.branco_t1 + s.nulo_t1, s.branco_t2 + s.nulo_t2
    s["comp1"], s["comp2"] = s.v1 + s.outros_t1 + s.bn1, s.v2 + s.bn2
    s["cod5"] = s.cod_municipio.str.zfill(5)
    return s[(s.v1 > 0) & (s.v2 > 0)]


def quem(df: pd.DataFrame, t: int) -> pd.Series:
    return pd.Series(np.where(df[f"lula_t{t}"] > df[f"flavio_t{t}"], "L", "F"), index=df.index)


def somar(df: pd.DataFrame, chave) -> pd.DataFrame:
    cols = ["lula_t1", "flavio_t1", "outros_t1", "bn1", "comp1", "lula_t2", "flavio_t2", "bn2", "comp2", "v1", "v2"]
    g = df.groupby(chave, as_index=False)[cols].sum()
    g["n"] = df.groupby(chave).size().values
    g["l1"], g["l2"] = 100 * g.lula_t1 / g.v1, 100 * g.lula_t2 / g.v2
    g["w1"], g["w2"] = quem(g, 1), quem(g, 2)
    g["dm"] = (g.lula_t2 - g.flavio_t2) - (g.lula_t1 - g.flavio_t1)     # variação da vantagem de Lula, em votos
    g["dl"], g["df"] = g.lula_t2 - g.lula_t1, g.flavio_t2 - g.flavio_t1
    return g


def transicao(g: pd.DataFrame) -> dict:
    """Quantas unidades (e quantos votos válidos do 2º turno) em cada caso: LL, FL (Lula virou), LF (Flávio virou), FF."""
    out = {}
    for a in "LF":
        for b in "LF":
            x = g[(g.w1 == a) & (g.w2 == b)]
            out[a + b] = dict(n=int(len(x)), votos_2t=int(x.v2.sum()), lula=int(x.lula_t2.sum()), flavio=int(x.flavio_t2.sum()))
    return out


def captura(df: pd.DataFrame) -> dict:
    """Regressão ecológica por seção: de cada grupo do 1º turno, quanto foi para Lula e quanto para Flávio no 2º (sem intercepto, coeficientes ≥ 0)."""
    d = df.comp2 - df.comp1
    X = np.column_stack([df.lula_t1, df.flavio_t1, df.outros_t1, df.bn1, d.clip(lower=0)]).astype(float)
    bl, _ = nnls(X, df.lula_t2.values.astype(float))
    bf, _ = nnls(X, df.flavio_t2.values.astype(float))
    return dict(outros_para_lula=round(float(bl[2]), 2), outros_para_flavio=round(float(bf[2]), 2), lula_fica=round(float(bl[0]), 2), flavio_fica=round(float(bf[1]), 2),
                novos_para_lula=round(float(bl[4]), 2), novos_para_flavio=round(float(bf[4]), 2), outros_1t=int(df.outros_t1.sum()), n_secoes=int(len(df)))


def linha_cidade(r) -> dict:
    return dict(uf=r.uf, municipio=r.municipio.title(), votos=int(r.v2), l1=r1(r.l1), l2=r1(r.l2), dpp=r1(r.l2 - r.l1), dm=int(r.dm), dl=int(r.dl), df=int(r["df"]), w1=r.w1, w2=r.w2)


def capitais() -> set:
    c = pd.read_csv("datasets/tse-presidente-capitais.csv", dtype={"cod_municipio": str})
    return set(c[(c.ano == 2026) & (c.turno == 2)].cod_municipio.str.zfill(5))


def main() -> None:
    s = carregar()
    s["w1"], s["w2"] = quem(s, 1), quem(s, 2)
    mun = somar(s, ["uf", "cod5", "municipio"])
    zona = somar(s, ["uf", "cod5", "municipio", "zona"])
    uf = somar(s, "uf")
    br = somar(s.assign(tudo="BR"), "tudo").iloc[0]
    uf["regiao"] = uf.uf.map(UF_REG)

    # ---- transições em quatro escalas
    trans = dict(secao=transicao(s.assign(w1=quem(s, 1), w2=quem(s, 2))), zona=transicao(zona), municipio=transicao(mun), uf=transicao(uf))

    # ---- UFs
    caps = {u: captura(s[s.uf == u]) for u in uf.uf}
    ufs = []
    for _, r in uf.sort_values("l2").iterrows():
        x, sm = s[s.uf == r.uf], mun[mun.uf == r.uf]
        ufs.append(dict(uf=r.uf, regiao=REGIAO[r.regiao], l1=r1(r.l1), l2=r1(r.l2), dpp=r1(r.l2 - r.l1), dl=int(r.dl), df=int(r["df"]), w1=r.w1, w2=r.w2,
                        secoes=int(len(x)), sec_virou_lula=int(((x.w1 == "F") & (x.w2 == "L")).sum()), sec_virou_flavio=int(((x.w1 == "L") & (x.w2 == "F")).sum()),
                        mun=int(len(sm)), mun_virou_lula=int(((sm.w1 == "F") & (sm.w2 == "L")).sum()), mun_virou_flavio=int(((sm.w1 == "L") & (sm.w2 == "F")).sum()),
                        mun_lula=int((sm.w2 == "L").sum()), cap=r1(100 * r.dl / (r.dl + r["df"])) if r.dl + r["df"] > 0 else None, outros_1t=int(r.outros_t1)))
    regs = []
    for k, nome in REGIAO.items():
        x, g = s[s.uf.map(UF_REG) == k], uf[uf.regiao == k]
        c = captura(x)
        regs.append(dict(regiao=nome, l1=r1(100 * g.lula_t1.sum() / g.v1.sum()), l2=r1(100 * g.lula_t2.sum() / g.v2.sum()), dl=int(g.dl.sum()), df=int(g["df"].sum()), **c))
    nac_cap = captura(s)

    # ---- cidades (≥ 100 mil votos válidos no 2º turno)
    grandes = mun[mun.v2 >= 100000].copy()
    topo = lambda df, col, asc, n=8: [linha_cidade(r) for _, r in df.sort_values(col, ascending=asc).head(n).iterrows()]
    cidades = dict(
        lula_virou=topo(mun[(mun.w1 == "F") & (mun.w2 == "L")], "dm", False, 10),
        flavio_virou=topo(mun[(mun.w1 == "L") & (mun.w2 == "F")], "dm", True, 3),
        flavio_manteve=topo(mun[(mun.w1 == "F") & (mun.w2 == "F")], "flavio_t2", False, 10),
        lula_manteve=topo(mun[(mun.w1 == "L") & (mun.w2 == "L")], "lula_t2", False, 10),
        maior_vantagem_lula=topo(mun.assign(vant=mun.lula_t2 - mun.flavio_t2), "vant", False, 8),
        maior_vantagem_flavio=topo(mun.assign(vant=mun.lula_t2 - mun.flavio_t2), "vant", True, 8),
        maior_vantagem_lula_pct=topo(grandes, "l2", False, 8), maior_vantagem_flavio_pct=topo(grandes, "l2", True, 8),
        maior_ganho_lula_pp=[linha_cidade(r) for _, r in grandes.assign(d=grandes.l2 - grandes.l1).sort_values("d", ascending=False).head(8).iterrows()],
        menor_ganho_lula_pp=[linha_cidade(r) for _, r in grandes.assign(d=grandes.l2 - grandes.l1).sort_values("d").head(8).iterrows()],
        capitais=[linha_cidade(r) for _, r in mun[mun.cod5.isin(capitais())].sort_values("l2").iterrows()])
    # ---- comparação com 2022 (2º turno), por município
    m22 = pd.read_csv("datasets/tse-presidente-municipio.csv", dtype={"cod_municipio": str})
    m22 = m22[(m22.ano == 2022) & (m22.turno == 2)][["cod_municipio", "pct_pt_dois"]].rename(columns={"pct_pt_dois": "l22"})
    m22["cod5"] = m22.cod_municipio.str.zfill(5)
    j = mun.merge(m22[["cod5", "l22"]], on="cod5", how="left")
    j["d22"] = j.l2 - j.l22
    ok = j.dropna(subset=["l22"]).copy()
    ok["reg"] = ok.uf.map(UF_REG)
    pond = lambda x, col: float(np.average(x[col], weights=x.v2))
    cmp22 = dict(n=int(len(ok)), mais_lula=int((ok.d22 > 0).sum()), menos_lula=int((ok.d22 < 0).sum()), mediana_pp=r1(ok.d22.median()), media_pp=r1(ok.d22.mean()),
                 ponderada_pp=r1(pond(ok, "d22")),
                 por_regiao=[dict(regiao=REGIAO[k], pp=r1(pond(x, "d22")), mediana=r1(x.d22.median()), mais_lula=int((x.d22 > 0).sum()), n=int(len(x))) for k, x in ok.groupby("reg")],
                 por_porte=[dict(porte=nome, n=int(len(x)), mediana=r1(x.d22.median()), ponderada=r1(pond(x, "d22")), mais_lula=int((x.d22 > 0).sum()), votos=int(x.v2.sum()))
                            for nome, x in ok.groupby(pd.cut(ok.v2, [0, 10000, 50000, 200000, 1e9], labels=["até 10 mil votos", "10 a 50 mil", "50 a 200 mil", "mais de 200 mil"]), observed=True)],
                 maiores_altas=[dict(**linha_cidade(r), l22=r1(r.l22)) for _, r in ok[ok.v2 >= 100000].sort_values("d22", ascending=False).head(8).iterrows()],
                 maiores_quedas=[dict(**linha_cidade(r), l22=r1(r.l22)) for _, r in ok[ok.v2 >= 100000].sort_values("d22").head(8).iterrows()])
    # ---- dispersão de municípios e histograma de seções
    pts = mun[mun.v2 >= 5000]
    disp = [[round(a, 1), round(b, 1), int(c), u] for a, b, c, u in zip(pts.l1, pts.l2, pts.v2, pts.uf)]
    faixas = list(range(0, 101, 5))
    h1, _ = np.histogram(100 * s.lula_t1 / s.v1, bins=faixas)
    h2, _ = np.histogram(100 * s.lula_t2 / s.v2, bins=faixas)
    saida = dict(brasil=dict(l1=r1(br.l1), l2=r1(br.l2), dl=int(br.dl), df=int(br["df"]), outros_1t=int(br.outros_t1), bn1=int(br.bn1), bn2=int(br.bn2), comp1=int(br.comp1), comp2=int(br.comp2),
                             secoes=int(len(s)), municipios=int(len(mun)), zonas=int(len(zona)), lula_t2=int(br.lula_t2), flavio_t2=int(br.flavio_t2)),
                 transicao=trans, ufs=ufs, regioes=regs, captura_br=nac_cap, cidades=cidades, vs2022=cmp22, dispersao=disp,
                 histograma=dict(faixas=faixas[:-1], t1=h1.tolist(), t2=h2.tolist()))
    json.dump(saida, open("modelos/secoes-2026.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    t = trans
    print("seções:", {k: v["n"] for k, v in t["secao"].items()}, "| municípios:", {k: v["n"] for k, v in t["municipio"].items()}, "| zonas:", {k: v["n"] for k, v in t["zona"].items()})
    print("captura BR:", nac_cap)


if __name__ == "__main__":
    main()

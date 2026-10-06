"""Gera analise-governo.html e analise-bancada.html (análises do 1º turno de 2026 no RS) a partir de apps/analise-*.template.html.

Entradas: datasets/resultado-2026-rs-*.csv (resultado preliminar, com a fonte de cada linha), TSE 2022 (datasets/), pesquisas e modelo do RS
(rs_modelo.py) e a previsão da bancada (rs_bancada.py, cenário padrão λ=0,25 μ=0,5). Só mostra número com fonte; célula vazia = não localizei."""
import json
import unicodedata

import numpy as np
import pandas as pd

import nav
import rs_bancada
import rs_modelo as rm
from rs_dados import carregar

D = "datasets/"
r1 = lambda x: None if pd.isna(x) else round(float(x), 2)
norm = lambda s: "".join(c for c in unicodedata.normalize("NFD", s.upper()) if unicodedata.category(c) != "Mn")


def pagina(tpl, saida, dados):
    html = open(f"apps/{tpl}", encoding="utf-8").read().replace("__NAV__", nav.html(saida)).replace("__DATA__", json.dumps(dados, ensure_ascii=False))
    open(saida, "w", encoding="utf-8").write(html)
    print(saida, len(html) // 1024, "KB")


# ------------------------------------------------------------------ governo do RS
def governo():
    res = pd.read_csv(D + "resultado-2026-rs-governador.csv")
    g = res[res.cargo == "GOVERNADOR"]
    cand = [dict(nome=r.candidato, partido=r.partido if isinstance(r.partido, str) else "", votos=None if pd.isna(r.votos) else int(r.votos), pct=float(r.pct)) for r in g.itertuples()]
    tot = res[res.cargo == "GOVERNADOR_TOTAIS"].iloc[0]
    pres = {r.candidato: dict(votos=int(r.votos), pct=float(r.pct)) for r in res[res.cargo == "PRESIDENTE_NO_RS"].itertuples()}
    nac22 = pd.read_csv(D + "tse-presidente-nacional.csv").query("ano == 2022 and turno == 1").iloc[0]
    br = pd.read_csv(D + "resultado-2026-turno1.csv").query("uf == 'BR'").iloc[0]
    out = dict(cand=cand, validos=int(tot.votos), pres26=pres, nac=dict(L22=r1(nac22.pct_pt_validos), B22=r1(nac22.pct_antipt_validos), L26=float(br.lula), B26=float(br.flavio)))

    # 2022: blocos do governador (1º turno) e candidatos
    m = carregar()
    m1 = m[(m.ano == 2022) & (m.turno == 1)]
    bl = m1.groupby("bloco").votos.sum()
    out["blocos22"] = {b: round(100 * float(bl[b] / bl.sum()), 2) for b in "EDC" if b in bl}
    c22 = m1.groupby(["nome", "partido", "bloco"], as_index=False).votos.sum().assign(pct=lambda d: 100 * d.votos / d.votos.sum()).sort_values("pct", ascending=False).head(5)
    out["cand22"] = [dict(nome=r.nome.title(), partido=r.partido, bloco=r.bloco, pct=round(r.pct, 2)) for r in c22.itertuples()]

    # presidente no RS em 2022 e nas cidades
    uf = pd.read_csv(D + "tse-presidente-uf.csv").query("ano == 2022 and turno == 1 and uf == 'RS'").iloc[0]
    out["pres22"] = dict(L=round(uf.pct_pt_validos, 2), B=round(uf.pct_antipt_validos, 2))
    mun = pd.read_csv(D + "tse-presidente-municipio.csv").query("uf == 'RS' and ano == 2022 and turno == 1")
    mun = mun.assign(k=mun.municipio.map(norm)).set_index("k")
    cid = pd.read_csv(D + "resultado-2026-rs-cidades.csv")
    linhas = []
    for r in cid.itertuples():
        a = mun.loc[norm(r.municipio)]
        lula = r.lider_presidente.startswith("Lula")
        base = 100 * (a.votos_pt if lula else a.votos_antipt) / a.validos
        linhas.append(dict(municipio=r.municipio, lg=r.lider_governador, pg=float(r.pct_governador), lp=r.lider_presidente, pp=float(r.pct_presidente),
                           base22=round(base, 1), d=round(float(r.pct_presidente) - base, 1), L22=round(100 * a.votos_pt / a.validos, 1), B22=round(100 * a.votos_antipt / a.validos, 1), obs=r.obs if isinstance(r.obs, str) else ""))
    out["cidades"] = linhas

    # modelo e pesquisas (referência: pesquisas até 2/10)
    d = rm.preparar()
    par = rm.parametros(d)
    rng = np.random.default_rng(1)
    L = np.linalg.cholesky(np.array(par["cov"]))
    x = rng.standard_normal((20000, 2)) @ L.T
    e = np.exp(np.column_stack([np.zeros(20000), np.array(par["mu"]) + x]))
    s = e / e.sum(1, keepdims=True) * (1 - par["rbar"])
    q = np.percentile(s, [5, 50, 95], axis=0) * 100
    ch = rm.chances(par)
    out["modelo"] = dict(data=str(par["data"]), Z=[r1(v) for v in q[:, 0]], B=[r1(v) for v in q[:, 1]], S=[r1(v) for v in q[:, 2]], O=r1(100 * par["rbar"]),
                         eleito=ch["eleito"], vence_1t=ch["vence_1t"], segundo_turno=ch["segundo_turno"], sistematico=rm.SISTEMATICO_1T_PP)
    u = d.sort_values("data").groupby("instituto").tail(1)
    out["pesq"] = [dict(inst=r.instituto, campo=str(r.data.date()), Z=r1(100 * r.z), B=r1(100 * r.b), S=r1(100 * r.s), O=r1(100 * r.r)) for r in u.itertuples()]
    return out


# ------------------------------------------------------------------ bancada do RS
def bancada():
    pac = rs_bancada.construir()
    res = pd.read_csv(D + "resultado-2026-rs-bancada.csv")
    top = pd.read_csv(D + "resultado-2026-rs-mais-votados.csv")
    out = dict(cadeiras=pac["cadeiras"], bloco_nome=pac["bloco_nome"], federacoes=pac["federacoes"],
               top=[dict(cargo=r.cargo, nome=r.nome, partido=r.partido, votos=int(r.votos), votos22=None if pd.isna(r.votos_2022) else int(r.votos_2022)) for r in top.itertuples()])
    for cargo in ("DF", "DE"):
        r = res[res.cargo == cargo]
        assert r.cadeiras.sum() == pac["cadeiras"][cargo], cargo
        real_p = {p: int(n) for p, n in zip(r.partido, r.cadeiras)}
        lista = lambda p: rs_bancada.lista_2026(rs_bancada.sucessor(p))
        real_l = r.assign(l=r.partido.map(lista)).groupby("l").cadeiras.sum()
        prev = pac["previsao"][cargo]["0.25_0.5"]
        listas = []
        for l in prev["listas"]:
            if l["med"] < 0.05 and real_l.get(l["lista"], 0) == 0:
                continue
            listas.append({**{k: l[k] for k in ("lista", "membros", "blocos", "eleitos_2022", "atual", "med", "mediana", "p10", "p90")}, "real": int(real_l.get(l["lista"], 0))})
        sem = set(real_l.index) - {l["lista"] for l in listas}
        assert not sem, sem
        blocos = {}
        for b in "ECD":
            blocos[b] = dict(real=int(sum(n for p, n in real_p.items() if rs_bancada.bloco(p) == b)),
                             e22=int(sum(n for p, n in pac["atual"][cargo]["eleitos_2022"].items() if rs_bancada.bloco(rs_bancada.sucessor(p)) == b)),
                             atual=int(sum(n for p, n in pac["atual"][cargo]["atual"].items() if rs_bancada.bloco(rs_bancada.sucessor(p)) == b)), **prev["blocos"][b])
        out[cargo] = dict(listas=listas, blocos=blocos, real_partidos=real_p, e22_partidos=pac["atual"][cargo]["eleitos_2022"], atual_partidos=pac["atual"][cargo]["atual"],
                          trocadas=round(sum(abs(l["med"] - l["real"]) for l in listas) / 2, 1))
    # pós-fato: mesma previsão, mas com o resultado REAL do governador (blocos: Brizola; Souza + Maranata; Zucco + nanicos) no lugar das pesquisas
    gv = pd.read_csv(D + "resultado-2026-rs-governador.csv").query("cargo == 'GOVERNADOR'").set_index("candidato").pct
    blk = rs_bancada.blocos_governador()
    real26 = {"E": gv["Juliana Brizola"] / 100, "C": (gv["Gabriel Souza"] + gv["Marcelo Maranata"]) / 100}
    real26["D"] = 1 - real26["E"] - real26["C"]
    out["gov_blocos"] = dict(pesquisas={k: round(100 * v, 2) for k, v in blk[2026].items()}, real={k: round(100 * v, 2) for k, v in real26.items()})
    blk[2026] = real26
    out["posthoc"] = {}
    for cargo in ("DF", "DE"):
        real_l = pd.read_csv(D + "resultado-2026-rs-bancada.csv").query("cargo == @cargo")
        real_l = real_l.assign(l=real_l.partido.map(lambda p: rs_bancada.lista_2026(rs_bancada.sucessor(p)))).groupby("l").cadeiras.sum()
        out["posthoc"][cargo] = {}
        for lam in (0.0, 0.25, 0.5):
            p = rs_bancada.prever(cargo, lam, 0.5, "todos", S=4000, blk=blk)
            ls = {l["lista"]: l for l in p["listas"]}
            tr = sum(abs(ls.get(k, {"med": 0})["med"] - real_l.get(k, 0)) for k in set(ls) | set(real_l.index)) / 2
            out["posthoc"][cargo][str(lam)] = dict(trocadas=round(tr, 1), blocos=p["blocos"],
                                                     pl=dict(med=ls["PL"]["med"], p10=ls["PL"]["p10"], p90=ls["PL"]["p90"], real=int(real_l.get("PL", 0))))
    out["backtest_med"] = round(float(pd.DataFrame(pac["backtest"]["linhas"]).query("lam == 0.25").trocadas.mean()), 1)
    return out


if __name__ == "__main__":
    pagina("analise-governo.template.html", "analise-governo.html", governo())
    pagina("analise-bancada.template.html", "analise-bancada.html", bancada())

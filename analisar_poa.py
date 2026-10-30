"""Porto Alegre por zona eleitoral: presidente (2018, 2022, 2026) e governador (2018, 2022, 2026), e o 2026 por seção e local de votação.

  python analisar_poa.py
Entradas: datasets/tse-portoalegre-zona.csv (fetch_tse_poa.py) e datasets/tse-presidente-secao-2026.csv.gz (fetch_tse_secoes.py). Saída: modelos/poa.json.
Nos dois turnos de presidente, "% do PT" é PT/(PT+adversário) (Haddad em 2018, Lula em 2022 e 2026), como no resto do site. As porcentagens do governador são sobre os votos nominais."""
import json

import numpy as np
import pandas as pd

PT_PRES = {2018: "FERNANDO HADDAD", 2022: "LULA", 2026: "LULA"}
ADV_PRES = {2018: "JAIR BOLSONARO", 2022: "JAIR BOLSONARO", 2026: "FLAVIO BOLSONARO"}
r1 = lambda x: round(float(x), 1)


def pres_dois(d: pd.DataFrame, ano: int, turno: int, zona=None) -> dict:
    x = d[(d.ano == ano) & (d.turno == turno) & (d.cargo == "Presidente")]
    if zona is not None:
        x = x[x.zona == zona]
    v = x.groupby("candidato").votos.sum()
    pt, adv = int(v.get(PT_PRES[ano], 0)), int(v.get(ADV_PRES[ano], 0))
    return dict(pt=pt, adv=adv, validos=int(v.sum()), pct=r1(100 * pt / (pt + adv)), pct_validos=r1(100 * pt / v.sum()), pct_adv_validos=r1(100 * adv / v.sum()))


def gov(d: pd.DataFrame, ano: int, turno: int, zona=None) -> list:
    x = d[(d.ano == ano) & (d.turno == turno) & (d.cargo == "Governador")]
    if zona is not None:
        x = x[x.zona == zona]
    v = x.groupby(["candidato", "partido"]).votos.sum().sort_values(ascending=False)
    t = v.sum()
    return [dict(candidato=c.title(), partido=p, votos=int(n), pct=r1(100 * n / t)) for (c, p), n in v.items() if n / t >= 0.02]


def main() -> None:
    d = pd.read_csv("datasets/tse-portoalegre-zona.csv")
    zonas = sorted(d.zona.unique())
    # ---- totais da cidade
    cidade = dict(presidente={f"{a}_{t}": pres_dois(d, a, t) for a in (2018, 2022, 2026) for t in (1, 2)},
                  governador={f"{a}_{t}": gov(d, a, t) for a, t in [(2018, 1), (2018, 2), (2022, 1), (2022, 2), (2026, 1)]})
    # ---- por zona
    s = pd.read_csv("datasets/tse-presidente-secao-2026.csv.gz", dtype={"cod_municipio": str, "zona": str, "secao": str})
    s = s[s.municipio == "PORTO ALEGRE"].copy()
    s["zona"] = s.zona.astype(int)
    s["v1"], s["v2"] = s.lula_t1 + s.flavio_t1, s.lula_t2 + s.flavio_t2
    s["w1"], s["w2"] = np.where(s.lula_t1 > s.flavio_t1, "L", "F"), np.where(s.lula_t2 > s.flavio_t2, "L", "F")
    z_out = []
    for z in zonas:
        sz = s[s.zona == z]
        locais = sz.groupby("local").size().sort_values(ascending=False).head(3).index.str.title().tolist()
        p = {f"{a}_{t}": pres_dois(d, a, t, z) for a in (2018, 2022, 2026) for t in (1, 2)}
        g26, g22, g18 = gov(d, 2026, 1, z), gov(d, 2022, 2, z), gov(d, 2018, 2, z)
        z_out.append(dict(zona=int(z), secoes=int(len(sz)), locais=locais, presidente=p, gov_2026_1=g26, gov_2022_2=g22, gov_2018_2=g18, gov_2022_1=gov(d, 2022, 1, z), gov_2018_1=gov(d, 2018, 1, z),
                          dl=int(sz.lula_t2.sum() - sz.lula_t1.sum()), df=int(sz.flavio_t2.sum() - sz.flavio_t1.sum()), sec_virou_lula=int(((sz.w1 == "F") & (sz.w2 == "L")).sum()),
                          sec_virou_flavio=int(((sz.w1 == "L") & (sz.w2 == "F")).sum()), sec_lula_2t=int((sz.w2 == "L").sum())))
    # ---- seções e locais de votação em 2026
    trans = {a + b: int(((s.w1 == a) & (s.w2 == b)).sum()) for a in "LF" for b in "LF"}
    loc = s.groupby(["zona", "local", "endereco"], as_index=False)[["lula_t1", "flavio_t1", "lula_t2", "flavio_t2", "v1", "v2"]].sum()
    loc["secoes"] = s.groupby(["zona", "local", "endereco"]).size().values
    loc = loc[loc.v2 >= 800].copy()
    loc["l1"], loc["l2"] = 100 * loc.lula_t1 / loc.v1, 100 * loc.lula_t2 / loc.v2
    loc["dpp"] = loc.l2 - loc.l1
    lin = lambda r: dict(zona=int(r.zona), local=r.local.title(), endereco=r.endereco.title(), secoes=int(r.secoes), votos=int(r.v2), l1=r1(r.l1), l2=r1(r.l2), dpp=r1(r.dpp))
    locais = dict(n=int(len(loc)), mais_lula=[lin(r) for _, r in loc.sort_values("l2", ascending=False).head(10).iterrows()],
                  mais_flavio=[lin(r) for _, r in loc.sort_values("l2").head(10).iterrows()],
                  maior_ganho=[lin(r) for _, r in loc.sort_values("dpp", ascending=False).head(8).iterrows()],
                  menor_ganho=[lin(r) for _, r in loc.sort_values("dpp").head(8).iterrows()],
                  virou_lula=[lin(r) for _, r in loc[(loc.l1 < 50) & (loc.l2 > 50)].sort_values("v2", ascending=False).head(10).iterrows()],
                  virou_flavio=[lin(r) for _, r in loc[(loc.l1 > 50) & (loc.l2 < 50)].sort_values("v2", ascending=False).head(10).iterrows()],
                  lula_ganha=int((loc.l2 > 50).sum()), flavio_ganha=int((loc.l2 <= 50).sum()), virou_lula_n=int(((loc.l1 < 50) & (loc.l2 > 50)).sum()), virou_flavio_n=int(((loc.l1 > 50) & (loc.l2 < 50)).sum()))
    h1, _ = np.histogram(100 * s.lula_t1 / s.v1, bins=range(0, 101, 5))
    h2, _ = np.histogram(100 * s.lula_t2 / s.v2, bins=range(0, 101, 5))
    # ---- o voto casado: Lula (1º turno) contra Brizola no governador (1º turno), por zona
    casado = [dict(zona=z["zona"], lula=z["presidente"]["2026_1"]["pct_validos"], brizola=next((c["pct"] for c in z["gov_2026_1"] if c["candidato"] == "Juliana Brizola"), None),
                   zucco=next((c["pct"] for c in z["gov_2026_1"] if c["candidato"] == "Zucco"), None), flavio=z["presidente"]["2026_1"]["pct_adv_validos"]) for z in z_out]
    json.dump(dict(cidade=cidade, zonas=z_out, secoes=dict(n=int(len(s)), transicao=trans, hist1=h1.tolist(), hist2=h2.tolist(), votos_virou_lula=int(s[(s.w1 == "F") & (s.w2 == "L")].v2.sum())),
                   locais=locais, casado=casado), open("modelos/poa.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(json.dumps(cidade["presidente"], ensure_ascii=False)[:900]); print(trans, locais["lula_ganha"], locais["flavio_ganha"])
    for z in z_out:
        print(z["zona"], [z["presidente"][k]["pct"] for k in ("2018_2", "2022_2", "2026_1", "2026_2")], z["gov_2026_1"][:2], z["locais"][:1])


if __name__ == "__main__":
    main()

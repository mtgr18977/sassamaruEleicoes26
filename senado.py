"""Senado 2026: 54 das 81 cadeiras (2 por UF), resultado do 1º turno, ocupantes de hoje e a aritmética do Senado que toma posse em 2027.

Dados (todos oficiais): datasets/tse-senado-2018.csv e tse-senado-2026.csv (TSE, votação por candidato; fetch_tse_senado.py) e
datasets/senado-atual.csv (API de dados abertos do Senado; os 54 com mandato até 1/2/2027 são as cadeiras em disputa e os 27 com
mandato até 2031 ficam). Não há modelo próprio do Senado no repositório: a comparação "esperado × resultado" usa duas referências
ingênuas (manter o ocupante de hoje; seguir o bloco que venceu a presidencial de 2022 na UF), declaradas como tal."""
import unicodedata

import pandas as pd

import rs_bancada as rb

D = "datasets/"
SUCESSAO = {"PSL": "UNIÃO", "PHS": "PODE", "PRP": "PRD", "PATRI": "PRD"}          # além de rb.RENOME e rb.SUCESSAO_2026
# Ocupantes que concorreram com nome de urna diferente do parlamentar (mesma UF e mesmo partido ou partido de origem; conferido à mão)
APELIDOS = {"SERGIO PETECAO": "PETECAO", "RENAN CALHEIROS": "RENAN", "RANDOLFE RODRIGUES": "RANDOLFE", "LEILA BARROS": "LEILA DO VOLEI",
            "WEVERTON": "WEVERTON ROCHA", "SORAYA THRONICKE": "SORAYA", "CARLOS FAVARO": "FAVARO", "VENEZIANO VITAL DO REGO": "VENEZIANO",
            "ALESSANDRO VIEIRA": "DELEGADO ALESSANDRO"}
MAIORIA, TRES_QUINTOS, DOIS_TERCOS, TOTAL = 41, 49, 54, 81
bloco = lambda p: "S" if p == "S/Partido" else rb.bloco(p)                  # sem partido: fora dos três blocos
def titulo(n):
    """Nome de urna em caixa de título, com as partículas em minúscula (SAMANDA DE LULA → Samanda de Lula)."""
    return " ".join(w.lower() if w.lower() in ("de", "da", "do", "dos", "das", "e") and i else w.capitalize() for i, w in enumerate(str(n).split()))


norm = lambda s: "".join(c for c in unicodedata.normalize("NFD", str(s).upper()) if unicodedata.category(c) != "Mn").strip()


def lin(p):
    """Partido → partido de 2026 (renomeações e fusões); 'S/Partido' fica como está."""
    p = rb.renomear(p)
    p = SUCESSAO.get(p, p)
    return rb.sucessor(p)


def carregar():
    a, b = pd.read_csv(D + "tse-senado-2018.csv"), pd.read_csv(D + "tse-senado-2026.csv")
    s = pd.read_csv(D + "senado-atual.csv")
    for d in (a, b):
        d["lin"] = d.partido.map(lin)
        d["bloco"] = d.lin.map(bloco)
        d["eleito"] = d.situacao == "ELEITO"
    s["lin"] = s.partido.map(lin)
    s["bloco"] = s.lin.map(bloco)
    return a, b, s


def contar(d, col="lin"):
    return d.groupby(col).size().to_dict()


def construir():
    a, b, s = carregar()
    e18, e26 = a[a.eleito], b[b.eleito]
    ocup = s[s.mandato_fim.str[:4] == "2027"]           # quem ocupa hoje as 54 cadeiras em disputa (inclui suplentes em exercício)
    fica = s[s.mandato_fim.str[:4] == "2031"]            # as 27 cadeiras de 2022
    assert len(e26) == 54 and len(ocup) == 54 and len(fica) == 27 and (e26.groupby("uf").size() == 2).all()

    # ---- listas: eleitos de 2018 (linhagem), ocupantes hoje, eleitos de 2026
    ps = sorted(set(e18.lin) | set(ocup.lin) | set(e26.lin))
    listas = [dict(lista=p, bloco=bloco(p), e18=int((e18.lin == p).sum()), atual=int((ocup.lin == p).sum()), real=int((e26.lin == p).sum())) for p in ps]
    listas.sort(key=lambda x: (-x["real"], -x["atual"], x["lista"]))
    blocos = {k: dict(e18=int((e18.bloco == k).sum()), atual=int((ocup.bloco == k).sum()), real=int((e26.bloco == k).sum())) for k in "EDCS"}

    # ---- por UF
    pres = pd.read_csv(D + "tse-presidente-uf.csv").query("ano == 2022 and turno == 1").set_index("uf")
    ufs = []
    for uf, g in b.groupby("uf"):
        g = g.sort_values("votos_validos", ascending=False)         # votos "anulados sub judice" (candidatura indeferida) ficam de fora
        tot = g.votos_validos.sum()
        el, ne = g[g.eleito], g[~g.eleito]
        seg, prim = el.iloc[1], ne.iloc[0]
        o = ocup[ocup.uf == uf]
        p22 = pres.loc[uf]
        ufs.append(dict(uf=uf, eleitos=[dict(nome=titulo(r.nome), partido=r.partido, bloco=r.bloco, votos=int(r.votos_validos), pct=round(100 * r.votos_validos / tot, 2)) for r in el.itertuples()],
                        vice=dict(nome=titulo(prim.nome), partido=prim.partido, votos=int(prim.votos_validos), pct=round(100 * prim.votos_validos / tot, 2)),
                        margem=int(seg.votos_validos - prim.votos_validos), margem_pp=round(100 * (seg.votos_validos - prim.votos_validos) / tot, 2), votos_validos=int(tot),
                        sub_judice=[f"{titulo(r.nome)} ({r.partido}): {int(r.votos):,}".replace(",", ".") for r in ne.itertuples() if r.votos > r.votos_validos and r.votos > prim.votos_validos],
                        ocupantes=[dict(nome=r.nome, partido=r.partido, bloco=r.bloco) for r in o.itertuples()],
                        d26=int((el.bloco == "D").sum()), datual=int((o.bloco == "D").sum()), d_pres22=2 if p22.pct_antipt_validos > p22.pct_pt_validos else 0,
                        pres22=dict(L=round(float(p22.pct_pt_validos), 1), B=round(float(p22.pct_antipt_validos), 1))))

    # ---- referências ingênuas × resultado (Direita; "trocadas" = metade da soma dos desvios por UF, como na aba da bancada do RS)
    ref = {}
    for nome, col in (("Manter o ocupante de hoje", "datual"), ("Seguir a presidencial de 2022 na UF", "d_pres22")):
        prev = sum(u[col] for u in ufs)
        certo = sum(1 for u in ufs if u[col] == u["d26"])
        ref[nome] = dict(direita=prev, trocadas=round(sum(abs(u[col] - u["d26"]) for u in ufs) / 2, 1), ufs_certas=certo)
    # ---- reeleição
    cands = set(zip(b.uf, b.nome.map(norm)))
    el_ids = set(zip(e26.uf, e26.nome.map(norm)))
    concorreu = reeleito = 0
    nao_concorreu = []
    for r in ocup.itertuples():
        k = norm(r.nome)
        k = APELIDOS.get(k, k)
        if (r.uf, k) in cands:
            concorreu += 1
            reeleito += (r.uf, k) in el_ids
        else:
            nao_concorreu.append(f"{r.nome} ({r.uf})")
    reel = dict(ocupantes=len(ocup), concorreram=concorreu, reeleitos=reeleito, nao_localizados=nao_concorreu)

    # ---- Senado de 2027: 27 que ficam + 54 eleitos
    novo = {}
    for p in sorted(set(fica.lin) | set(e26.lin)):
        novo[p] = dict(bloco=bloco(p), fica=int((fica.lin == p).sum()), eleitos=int((e26.lin == p).sum()))
    nb = {k: dict(fica=int((fica.bloco == k).sum()), eleitos=int((e26.bloco == k).sum())) for k in "EDCS"}
    hoje = {k: int((s.bloco == k).sum()) for k in "EDCS"}
    top = b.sort_values("votos_validos", ascending=False).head(10)
    mais = [dict(uf=r.uf, nome=titulo(r.nome), partido=r.partido, votos=int(r.votos_validos), eleito=bool(r.eleito)) for r in top.itertuples()]
    return dict(cadeiras=54, total=TOTAL, listas=listas, blocos=blocos, ufs=ufs, ref=ref, reel=reel, novo=novo, nb=nb, hoje=hoje, mais=mais,
                limiares=dict(maioria=MAIORIA, tres_quintos=TRES_QUINTOS, dois_tercos=DOIS_TERCOS), bloco_nome=rb.BNOME,
                gerado=str(pd.read_csv(D + "senado-atual.csv").acesso.iloc[0]))


if __name__ == "__main__":
    import json
    r = construir()
    print(json.dumps({k: r[k] for k in ("blocos", "ref", "reel", "nb", "hoje")}, ensure_ascii=False, indent=1))

"""Bancada do RS (Dep. Federal 31 cadeiras, Dep. Estadual 55): histórico, listas e previsão de 2026.

Previsão em três passos, os mesmos do resto do projeto (base = última eleição, ajuste pelas pesquisas, Monte Carlo):
 1. Votação por partido de 2022 (nominais + legenda) levada aos partidos de 2026 (sucessões: PTB/Patriota→PRD etc.).
    Eleitos que mudaram de partido levam uma fração μ da própria votação nominal (μ ASSUMIDO; mostrado em cenários).
 2. Cada partido é movido pela variação do seu bloco (Esquerda/Centro/Direita) nas pesquisas do governador em relação ao
    1º turno de 2022, elevada a λ (λ calibrado por backtest de 2010, 2014, 2018 e 2022; cenários mostram 0, ½ e 1).
 3. Votos de partidos viram votos de listas (federações de 2026; coligações proporcionais não existem mais), com ruído
    calibrado nos resíduos do backtest, e as cadeiras saem da regra eleitoral (quociente + maiores médias), simulada N vezes.
O alocador reproduz as 12 distribuições reais de 2002–2022 (exceto 1 cadeira em 2010 e 1 em 2018 no Dep. Federal, por regras
de candidato que não entram aqui) — ver `validar_alocador()`.
"""
import numpy as np
import pandas as pd

D = "datasets/"
CADEIRAS = {"DF": 31, "DE": 55}
ANOS = [2002, 2006, 2010, 2014, 2018, 2022]
# Renomeações que preservam a linhagem (valem para todos os anos)
RENOME = {"PMDB": "MDB", "PPB": "PP", "PFL": "UNIÃO", "DEM": "UNIÃO", "PR": "PL", "PRB": "REPUBLICANOS", "PT do B": "AVANTE", "PTN": "PODE",
          "PPS": "CIDADANIA", "SD": "SOLIDARIEDADE", "PEN": "PATRIOTA", "PATRI": "PATRIOTA", "PSDC": "DC", "PTC": "AGIR", "PC do B": "PCdoB",
          "PAN": "PTB", "PRP": "PATRIOTA"}
# Fusões e renomeações depois de 2022 (valem só para levar a votação de 2022 até 2026)
SUCESSAO_2026 = {"PTB": "PRD", "PATRIOTA": "PRD", "PSC": "PODE", "PROS": "SOLIDARIEDADE", "PMN": "MOBILIZA"}
# Federações registradas no TSE para 2026 (A Gazeta, ago/2026; conferir no TSE): nome -> partidos
FEDERACOES_2026 = {"Brasil da Esperança": ["PT", "PCdoB", "PV"], "PSOL Rede": ["PSOL", "REDE"], "PSDB Cidadania": ["PSDB", "CIDADANIA"],
                   "União Progressista": ["UNIÃO", "PP"], "Renovação Solidária": ["PRD", "SOLIDARIEDADE"]}
# Blocos como no resto do projeto (rs_dados.py), com PCdoB/Rede/UP à esquerda e o PSD no centro (ASSUMIDO: aproximação; ver tabela por partido)
ESQ = {"PT", "PDT", "PSOL", "PSB", "PV", "PSTU", "PCO", "PCB", "PCdoB", "REDE", "UP"}
CEN = {"MDB", "PSDB", "CIDADANIA", "PSD"}
bloco = lambda p: "E" if p in ESQ else "C" if p in CEN else "D"
BNOME = {"E": "Esquerda", "C": "Centro", "D": "Direita e demais"}


def renomear(p: str) -> str:
    return RENOME.get(p, p)


# ---------------------------------------------------------------- dados
def carregar():
    pl = pd.read_csv(D + "tse-legislativo-rs-partido-lista.csv")
    pl["partido"] = pl.partido.map(renomear)
    el = pd.read_csv(D + "tse-legislativo-rs-eleitos.csv")
    el["partido"] = el.partido.map(renomear)
    ls = pd.read_csv(D + "tse-legislativo-rs-listas.csv")
    un = pd.read_csv(D + "tse-legislativo-rs-partido.csv")
    un["partido"] = un.partido.map(renomear)
    at = pd.read_csv(D + "rs-bancada-atual.csv")
    for c in ("partido_2022", "partido_atual"):
        at[c] = at[c].map(renomear)
    return pl, el, ls, un, at


def votos_partido(pl, ano, cargo):
    g = pl[(pl.ano == ano) & (pl.cargo == cargo)].groupby("partido").votos.sum()
    return g / g.sum()


def blocos_governador():
    """% dos válidos por bloco no 1º turno do governador (histórico) e estimativa 2026 pelas pesquisas (mesma base de rs_modelo)."""
    import rs_modelo as rm
    from rs_dados import carregar as car
    m = car()
    est = m[m.turno == 1].groupby(["ano", "bloco"]).votos.sum().unstack()
    hist = (est.div(est.sum(axis=1), axis=0)).to_dict("index")
    d = rm.preparar()
    par = rm.parametros(d)
    e = np.array([1, *np.exp(par["mu"])])
    z, b, s = e / e.sum() * (1 - par["rbar"])
    dd = d[d.data <= rm.HOJE]
    w = rm._pesos(dd, rm.HOJE)
    cand = dd.zucco + dd.brizola + dd.souza + dd.maranata + dd.outros
    mar, out = float((w * dd.maranata / cand).sum() / w.sum()), float((w * dd.outros / cand).sum() / w.sum())
    hist[2026] = {"E": float(b), "C": float(s) + mar, "D": float(z) + out}      # Brizola; Souza + Maranata; Zucco + nanicos
    return {int(a): {k: float(v) for k, v in x.items()} for a, x in hist.items()}


# ---------------------------------------------------------------- regra eleitoral
def alocar(votos, n, regra="todos"):
    """Cadeiras por lista. votos: (L,) ou (S, L). Quociente eleitoral arredondado (fração >0,5 sobe), cadeiras inteiras para listas com
    ao menos 1 QE e sobras por maiores médias (divisor cadeiras+1). regra das sobras: 'qe' (só listas com 1 QE: 2002–2018),
    '80' (listas com 80% do QE: 2022) ou 'todos' (qualquer lista; ASSUMIDO para 2026, decisão do STF de 2024 sobre as sobras)."""
    v = np.atleast_2d(np.asarray(votos, float))
    qe = v.sum(1, keepdims=True) / n
    qe = np.where(qe > 1000, np.floor(qe + 0.5), qe)         # arredondamento do QE só faz sentido em contagem de votos (não em proporções)
    s = np.floor(v / qe)
    s[v < qe] = 0
    elig = {"qe": v >= qe, "80": v >= 0.8 * qe, "todos": np.ones_like(v, bool)}[regra]
    resto = (n - s.sum(1)).astype(int)
    rows = np.arange(len(v))
    for k in range(int(resto.max()) if len(resto) else 0):
        m = np.where(elig, v / (s + 1), -1.0)
        idx = m.argmax(1)
        ativo = resto > k
        s[rows[ativo], idx[ativo]] += 1
    return s.astype(int) if np.ndim(votos) == 2 else s[0].astype(int)


def regra_do_ano(ano):
    return "80" if ano == 2022 else "qe"


def validar_alocador():
    """Reproduz as cadeiras reais por lista a partir dos votos reais. Retorna DataFrame (ano, cargo, cadeiras trocadas)."""
    ls = pd.read_csv(D + "tse-legislativo-rs-listas.csv")
    out = []
    for (ano, cargo), g in ls.groupby(["ano", "cargo"]):
        s = alocar(g.votos.to_numpy(), CADEIRAS[cargo], regra_do_ano(ano))
        out.append(dict(ano=int(ano), cargo=cargo, trocadas=int(np.abs(s - g.cadeiras.to_numpy()).sum() // 2)))
    return pd.DataFrame(out)


# ---------------------------------------------------------------- previsão
def projetar(base, ratio, lam, bl=bloco, teto=(0.5, 2.0)):
    """Move a votação de cada partido pela variação do seu bloco elevada a lam (limitada a `teto`) e renormaliza."""
    f = pd.Series({p: np.clip(ratio.get(bl(p), 1.0), *teto) ** lam for p in base.index})
    v = base * f
    return v / v.sum()


def razoes(blk, a0, a1):
    return {b: blk[a1][b] / blk[a0][b] if blk[a0][b] > 0.02 else 1.0 for b in "ECD"}


def estrutura(pl, ano, cargo):
    """lista de cada partido no ano (dict partido -> lista)."""
    g = pl[(pl.ano == ano) & (pl.cargo == cargo)]
    return dict(zip(g.partido, g.lista.astype(str)))


def prever_pesquisa_listas(pv, estr):
    """soma votos de partidos por lista; partidos que não existiam na base ficam de fora (limite do método)."""
    s = pd.Series(pv).groupby(pd.Series(estr).reindex(pv.index)).sum()
    return s


def backtest(lams=(0.0, 0.5, 1.0), blk=None):
    """Prevê 2010, 2014, 2018 e 2022 a partir da eleição anterior com a estrutura de listas do ano previsto (conhecida) e compara as cadeiras.
    Retorna (linhas por λ/ano/cargo, resíduos de log-votação por partido)."""
    pl, el, ls, un, at = carregar()
    blk = blk or blocos_governador()
    linhas, resid = [], []
    for a0, a1 in zip(ANOS[:-1], ANOS[1:]):
        if a1 == 2006:
            continue
        for cargo in ("DF", "DE"):
            base, real = votos_partido(pl, a0, cargo), votos_partido(pl, a1, cargo)
            estr = estrutura(pl, a1, cargo)
            actual = ls[(ls.ano == a1) & (ls.cargo == cargo)].assign(lista=lambda d: d.lista.astype(str)).set_index("lista")
            for lam in lams:
                pv = projetar(base, razoes(blk, a0, a1), lam)
                lv = prever_pesquisa_listas(pv, estr).reindex(actual.index).fillna(0.0)
                s = alocar(lv.to_numpy() + 1e-9, CADEIRAS[cargo], regra_do_ano(a1))
                linhas.append(dict(lam=lam, ano=a1, cargo=cargo, trocadas=int(np.abs(s - actual.cadeiras.to_numpy()).sum() // 2)))
                for p in pv.index:
                    if pv[p] >= 0.01 and p in real.index and real[p] > 0:
                        resid.append(dict(lam=lam, ano=a1, cargo=cargo, partido=p, bloco=bloco(p), r=float(np.log(real[p] / pv[p]))))
    return pd.DataFrame(linhas), pd.DataFrame(resid)


def simular(pv, estr, n, regra, sig_b, sig_i, S=4000, seed=7):
    """Monte Carlo: votos de partido x ruído log-normal (choque comum do bloco + idiossincrático), soma por lista, aloca cadeiras.
    Retorna (nomes das listas, cadeiras (S, L), partidos, votos de partido simulados (S, P))."""
    rng = np.random.default_rng(seed)
    partidos = list(pv.index)
    bl = np.array([bloco(p) for p in partidos])
    zb = {b: rng.standard_normal(S) for b in "ECD"}
    sig = sig_i * (0.2 + 0.45 * np.exp(-pv.to_numpy() / 0.06))        # ruído maior para partido pequeno (resíduos do backtest: 0,24 acima de 10%, ~0,5 entre 3 e 10%, ~0,65 abaixo)
    eps = np.column_stack([sig_b * zb[b] for b in bl]) + sig[None, :] * rng.standard_normal((S, len(partidos)))
    v = pv.to_numpy()[None, :] * np.exp(eps)
    v = v / v.sum(1, keepdims=True)
    listas = sorted(set(estr[p] for p in partidos))
    M = np.array([[estr[p] == l for p in partidos] for l in listas], float)       # (L, P)
    lv = v @ M.T
    return listas, alocar(lv * 1e7, n, regra), partidos, v


def cobertura(lam, sig_b, sig_i, blk=None, S=2000):
    """Fração das cadeiras reais por lista (backtest 2010–2022) dentro do intervalo de 80% simulado, só para listas com ≥1 cadeira real ou prevista."""
    pl, el, ls, un, at = carregar()
    blk = blk or blocos_governador()
    dentro = tot = 0
    for a0, a1 in zip(ANOS[:-1], ANOS[1:]):
        if a1 == 2006:
            continue
        for cargo in ("DF", "DE"):
            base, estr = votos_partido(pl, a0, cargo), estrutura(pl, a1, cargo)
            pv = projetar(base, razoes(blk, a0, a1), lam)
            pv = pv[[p for p in pv.index if p in estr]]
            pv = pv / pv.sum()
            listas, seats, *_ = simular(pv, estr, CADEIRAS[cargo], regra_do_ano(a1), sig_b, sig_i, S=S)
            real = ls[(ls.ano == a1) & (ls.cargo == cargo)].assign(lista=lambda d: d.lista.astype(str)).set_index("lista").cadeiras
            lo, hi = np.percentile(seats, 10, axis=0), np.percentile(seats, 90, axis=0)
            for j, l in enumerate(listas):
                r = int(real.get(l, 0))
                if r > 0 or hi[j] > 0:
                    tot += 1
                    dentro += lo[j] - 1e-9 <= r <= hi[j] + 1e-9
    return dentro / tot, tot


# ---------------------------------------------------------------- 2026
SIG_B, SIG_I = 0.15, 1.1      # choque comum do bloco (log da votação) e escala do ruído por partido; calibrados para cobrir ~80% no backtest (ver `cobertura`)
LAM_PADRAO, MU_PADRAO = 0.25, 0.5
LAMS, MUS = (0.0, 0.25, 0.5), (0.0, 0.5, 1.0)


def sucessor(p):
    return SUCESSAO_2026.get(p, p)


def lista_2026(p):
    for nome, membros in FEDERACOES_2026.items():
        if p in membros:
            return nome
    return p


def base_2026(pl, at, cargo, mu):
    """Votação de 2022 nos partidos de 2026 (sucessões) com a votação nominal dos eleitos que trocaram de partido levada a mu."""
    b = votos_partido(pl, 2022, cargo)
    b = b.groupby(b.index.map(sucessor)).sum()
    for r in at[at.cargo == cargo].itertuples():
        de, para = sucessor(r.partido_2022), sucessor(r.partido_atual)
        if de != para:
            # votos nominais do eleito / total de votos válidos de 2022 no cargo (mesma escala de b, que soma 1)
            tot = pl[(pl.ano == 2022) & (pl.cargo == cargo)].votos.sum()
            mv = min(mu * r.votos_2022 / tot, b.get(de, 0.0))
            b[de] = b.get(de, 0.0) - mv
            b[para] = b.get(para, 0.0) + mv
    b = b[b > 0]
    return b / b.sum()


def seats_por_lista(df, cargo, mapa):
    """cadeiras (eleitos ou bancada atual) agrupadas nas listas de 2026."""
    return df.groupby(df.map(lambda p: lista_2026(sucessor(p)))).size() if mapa is None else None


def prever(cargo, lam, mu, regra="todos", S=6000, blk=None, seed=11):
    pl, el, ls, un, at = carregar()
    blk = blk or blocos_governador()
    base = base_2026(pl, at, cargo, mu)
    pv = projetar(base, razoes(blk, 2022, 2026), lam)
    estr = {p: lista_2026(p) for p in pv.index}
    listas, seats, partidos, v = simular(pv, estr, CADEIRAS[cargo], regra, SIG_B, SIG_I, S=S, seed=seed)
    idx = {l: j for j, l in enumerate(listas)}
    # cadeiras por bloco: cada lista reparte suas cadeiras entre os partidos pela votação simulada de cada um
    bl = np.array([bloco(p) for p in partidos])
    blocos = {}
    for b in "ECD":
        tot = np.zeros(S)
        for l, j in idx.items():
            cols = [i for i, p in enumerate(partidos) if estr[p] == l]
            lv = v[:, cols].sum(1)
            tot += seats[:, j] * v[:, [i for i in cols if bl[i] == b]].sum(1) / np.where(lv > 0, lv, 1)
        blocos[b] = tot
    el22 = el[(el.ano == 2022) & (el.cargo == cargo)].groupby(el.partido.map(lambda p: lista_2026(sucessor(p)))).cadeiras.sum()
    atual = at[at.cargo == cargo].groupby(at.partido_atual.map(lambda p: lista_2026(sucessor(p)))).size()
    pq = lambda a, q: float(np.percentile(a, q))
    linhas = []
    for l, j in idx.items():
        membros = [p for p in partidos if estr[p] == l]
        linhas.append(dict(lista=l, membros=membros if len(membros) > 1 else [], blocos=sorted({bloco(p) for p in membros}), voto_base=round(100 * float(base.reindex(membros).sum()), 2),
                           voto_2026=round(100 * float(pv.reindex(membros).sum()), 2), eleitos_2022=int(el22.get(l, 0)), atual=int(atual.get(l, 0)),
                           med=round(float(seats[:, j].mean()), 2), mediana=int(pq(seats[:, j], 50)), p10=int(pq(seats[:, j], 10)), p90=int(pq(seats[:, j], 90)),
                           p1=round(float((seats[:, j] >= 1).mean()), 3)))
    linhas.sort(key=lambda r: -r["med"])
    bl_out = {b: dict(med=round(float(x.mean()), 2), p10=round(pq(x, 10), 1), p90=round(pq(x, 90), 1)) for b, x in blocos.items()}
    return dict(listas=linhas, blocos=bl_out, qe=None)


# ---------------------------------------------------------------- pacote para a página
def enp(x):
    x = np.asarray(x, float)
    x = x / x.sum()
    return float(1 / (x ** 2).sum())


def historico(pl, el, ls, un, at):
    """séries 2002–2022 por cargo: cadeiras e votos por partido, blocos, nº efetivo de partidos, listas por eleição e blocos por região."""
    out = {}
    for cargo in ("DF", "DE"):
        seats = el[el.cargo == cargo].groupby(["ano", "partido"]).cadeiras.sum().unstack("ano").reindex(columns=ANOS).fillna(0).astype(int)
        votos = pl[pl.cargo == cargo].groupby(["ano", "partido"]).votos.sum().unstack("ano").reindex(columns=ANOS).fillna(0)
        share = 100 * votos / votos.sum()
        parts = [p for p in seats.index if seats.loc[p].sum() > 0 or share.loc[p].max() >= 2]
        parts = sorted(parts, key=lambda p: -share.loc[p].iloc[-3:].sum())
        bl_seats = {b: [int(seats[a][[p for p in seats.index if bloco(p) == b]].sum()) for a in ANOS] for b in "ECD"}
        bl_votes = {b: [round(float(share[a][[p for p in share.index if bloco(p) == b]].sum()), 2) for a in ANOS] for b in "ECD"}
        listas = {}
        for a in ANOS:
            g = ls[(ls.ano == a) & (ls.cargo == cargo)].sort_values("votos", ascending=False)
            tot = g.votos.sum()
            listas[str(a)] = [dict(nome=(r.nome if r.tipo == "coligacao" and isinstance(r.nome, str) and r.nome != "PARTIDO ISOLADO" else None), tipo=r.tipo,
                                   composicao=" / ".join(sorted({renomear(x.strip()) for x in str(r.composicao).replace(",", "/").split("/") if x.strip()})),
                                   votos=int(r.votos), pct=round(100 * r.votos / tot, 2), cadeiras=int(r.cadeiras)) for r in g.itertuples() if r.cadeiras > 0 or r.votos / tot >= 0.01]
        u = un[un.cargo == cargo].groupby(["ano", "unidade", "partido"]).votos.sum().reset_index()
        u["bloco"] = u.partido.map(bloco)
        ub = u.groupby(["ano", "unidade", "bloco"]).votos.sum().unstack("bloco").fillna(0)
        ub = 100 * ub.div(ub.sum(axis=1), axis=0)
        reg = {str(a): {un_: {b: round(float(ub.loc[(a, un_), b]), 2) for b in "ECD"} for un_ in ub.loc[a].index} for a in ANOS}
        out[cargo] = dict(anos=ANOS, partidos=parts, cadeiras={p: seats.loc[p].tolist() for p in parts}, voto={p: [round(float(x), 2) for x in share.loc[p]] for p in parts},
                          bloco_cadeiras=bl_seats, bloco_voto=bl_votes,
                          enp_voto=[round(enp(votos[a][votos[a] > 0]), 2) for a in ANOS], enp_cadeiras=[round(enp(seats[a][seats[a] > 0]), 2) for a in ANOS],
                          listas=listas, regioes=reg)
    return out


def atual_pacote(pl, el, ls, un, at):
    out = {}
    for cargo in ("DF", "DE"):
        a = at[at.cargo == cargo]
        mig = a[a.partido_2022 != a.partido_atual].groupby(["partido_2022", "partido_atual"]).size().reset_index(name="n")
        mig_sem_fusao = mig[mig.apply(lambda r: sucessor(r.partido_2022) != sucessor(r.partido_atual), axis=1)]
        out[cargo] = dict(eleitos_2022=a.groupby("partido_2022").size().to_dict(), atual=a.groupby("partido_atual").size().to_dict(),
                          migracao=[dict(de=r.partido_2022, para=r.partido_atual, n=int(r.n)) for r in mig_sem_fusao.sort_values("n", ascending=False).itertuples()],
                          trocaram=int(mig_sem_fusao.n.sum()), fonte=a.fonte.iloc[0], acesso=a.acesso.iloc[0])
    return out


def construir(S=6000):
    pl, el, ls, un, at = carregar()
    blk = blocos_governador()
    bt, _ = backtest(lams=LAMS, blk=blk)
    cob = {f"{lam}": cobertura(lam, SIG_B, SIG_I, blk, S=1500)[0] for lam in (LAM_PADRAO,)}
    prev = {}
    for cargo in ("DF", "DE"):
        prev[cargo] = {}
        for lam in LAMS:
            for mu in MUS:
                r = prever(cargo, lam, mu, "todos", S=S, blk=blk)
                prev[cargo][f"{lam}_{mu}"] = r
        prev[cargo]["alt_80"] = prever(cargo, LAM_PADRAO, MU_PADRAO, "80", S=S, blk=blk)
    return dict(cadeiras=CADEIRAS, historico=historico(pl, el, ls, un, at), atual=atual_pacote(pl, el, ls, un, at), blocos_gov=blk,
                bloco_nome=BNOME, bloco_de=bloco_partidos(pl), federacoes=FEDERACOES_2026, sucessao=SUCESSAO_2026, previsao=prev,
                backtest=dict(linhas=bt.to_dict("records"), medio={str(k): round(float(v), 2) for k, v in bt.groupby("lam").trocadas.mean().items()}, cobertura=cob),
                validacao=validar_alocador().to_dict("records"),
                params=dict(lam=LAM_PADRAO, mu=MU_PADRAO, lams=list(LAMS), mus=list(MUS), sig_b=SIG_B, sig_i=SIG_I, sims=S))


def bloco_partidos(pl):
    ps = sorted(pl[pl.ano == 2022].partido.unique())
    return {p: bloco(p) for p in ps}

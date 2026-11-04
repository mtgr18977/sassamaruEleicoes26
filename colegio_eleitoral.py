"""E se o presidente fosse eleito como nos EUA (Colégio Eleitoral, com delegados e distritos)? Resultado real do 2º turno de 2026.

  python colegio_eleitoral.py
Delegados: cadeiras da Câmara na UF (513, as de hoje) + 3 senadores por UF = 594; maioria 298. O voto do exterior (ZZ) não elege delegado.
O Brasil não tem distritos, então eu os desenho: em cada UF, junto as zonas eleitorais (município + zona, com o centroide do município) em tantos distritos quantas as cadeiras da UF,
com o mesmo total de votos válidos, por bisseção recursiva (corta ao longo do eixo de maior extensão no peso da fatia). Sem olhar voto: é um desenho neutro. Zona com mais de 30% da cota de um distrito é fatiada em partes iguais (capitais pequenas).
Um desenho "neutro" ainda depende de escolhas, então eu repito o sorteio do eixo de corte (semente fixa) para ver a faixa de resultados.
Entrada: datasets/tse-presidente-zona-2026.csv (TSE), datasets/tse-presidente-2turno-uf.csv, coordenadas dos municípios (IBGE, via datasets/municipios-coordenadas.csv).
Sai: modelos/colegio-eleitoral.json (a página: colegio-eleitoral.html)."""
import difflib
import json
import re
import unicodedata

import numpy as np
import pandas as pd

CADEIRAS = dict(AC=8, AL=9, AP=8, AM=8, BA=39, CE=22, DF=8, ES=10, GO=17, MA=18, MT=8, MS=8, MG=53, PA=17, PB=12, PR=30, PE=25, PI=10, RJ=46, RN=8, RS=31, RO=8, RR=8, SC=16, SP=70, SE=8, TO=8)
SENADORES = 3
UF_IBGE = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO", 21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ",
           35: "SP", 41: "PR", 42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}
# Nomes do TSE que o IBGE escreve diferente demais para o casamento por semelhança acertar (Campo Grande-RN hoje é Augusto Severo).
ALIAS = {("RN", "CAMPOGRANDE"): "AUGUSTOSEVERO", ("BA", "SANTATEREZINHA"): "SANTATERESINHA"}
SORTEIOS = 300
SEMENTE = 2026


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]", "", s)


def carregar() -> pd.DataFrame:
    """Uma linha por (município, zona) das UFs, com x/y do município. Quem não casa pelo nome casa pelo nome mais parecido da UF."""
    m = pd.read_csv("datasets/municipios-coordenadas.csv")
    m["uf"] = m.codigo_uf.map(UF_IBGE)
    m["k"] = m.nome.map(norm)
    z = pd.read_csv("datasets/tse-presidente-zona-2026.csv")
    z = z[z.uf.isin(CADEIRAS)].copy()
    z["k"] = z.municipio.map(norm)
    por_uf = {u: g.set_index("k")[["latitude", "longitude"]] for u, g in m.groupby("uf")}
    lat, lon = [], []
    for u, k in zip(z.uf, z.k):
        t = por_uf[u]
        k = ALIAS.get((u, k), k)
        if k not in t.index:
            achados = difflib.get_close_matches(k, list(t.index), n=1, cutoff=0.5)
            k = achados[0] if achados else None
        r = t.loc[k] if k else t.mean()  # sem par: centroide médio da UF (só Tabocão-TO)
        lat.append(float(r.latitude)); lon.append(float(r.longitude))
    z["lat"], z["lon"] = lat, lon
    z["peso"] = z.lula_t2 + z.flavio_t2
    # Zona com mais de 30% da cota de um distrito (só capitais pequenas, como Boa Vista) é fatiada em partes iguais, senão não dá para equilibrar o distrito.
    cota = z.groupby("uf").peso.transform("sum") / z.uf.map(CADEIRAS)
    z["fatias"] = np.ceil(z.peso / (0.3 * cota)).astype(int).clip(lower=1)
    z = z.loc[z.index.repeat(z.fatias)].copy()
    for c in ("lula_t2", "flavio_t2", "peso"):
        z[c] = z[c] / z.fatias
    return z.reset_index(drop=True)


def cortar(pontos: np.ndarray, peso: np.ndarray, ordem: np.ndarray, k: int, rng, ruido: float, saida: list) -> None:
    """Divide as unidades `ordem` (índices) em k distritos de peso parecido. ruido = desvio (graus) do eixo de corte em relação ao eixo principal."""
    if k == 1:
        saida.append(ordem)
        return
    p, w = pontos[ordem], peso[ordem]
    c = np.cov((p - np.average(p, axis=0, weights=w)).T, aweights=w) if len(ordem) > 2 else np.eye(2)
    val, vec = np.linalg.eigh(c)
    ang = np.arctan2(vec[1, -1], vec[0, -1]) + np.deg2rad(rng.normal(0, ruido)) if ruido else np.arctan2(vec[1, -1], vec[0, -1])
    proj = p @ np.array([np.cos(ang), np.sin(ang)])
    o = np.argsort(proj, kind="stable")
    acum = np.cumsum(w[o])
    k1 = k // 2
    alvo = acum[-1] * k1 / k
    i = int(np.searchsorted(acum, alvo))
    i = min(max(i if abs(acum[i] - alvo) <= abs(acum[max(i - 1, 0)] - alvo) else i - 1, 0), len(o) - 2)
    esq, dir_ = ordem[o[: i + 1]], ordem[o[i + 1:]]
    cortar(pontos, peso, esq, k1, rng, ruido, saida)
    cortar(pontos, peso, dir_, k - k1, rng, ruido, saida)


def distritos(z: pd.DataFrame, rng, ruido: float) -> np.ndarray:
    """Vetor com o número do distrito (0..N-1) de cada linha de z, UF a UF."""
    d = np.zeros(len(z), dtype=int)
    for u, n in CADEIRAS.items():
        idx = np.where(z.uf.values == u)[0]
        x = z.lon.values[idx] * np.cos(np.deg2rad(z.lat.values[idx].mean()))
        pts = np.column_stack([x, z.lat.values[idx]])
        # desempate estável: município, zona
        o = np.lexsort((z.zona.values[idx], z.cod_municipio.values[idx]))
        saida: list = []
        cortar(pts[o], z.peso.values[idx][o], np.arange(len(idx)), n, rng, ruido, saida)
        for j, s in enumerate(saida):
            d[idx[o][s]] = j
    return d


def placar(z: pd.DataFrame, d: np.ndarray) -> dict:
    """Para um desenho de distritos: vencedor de cada distrito, da UF e os delegados em cada regra."""
    z = z.assign(d=d)
    g = z.groupby(["uf", "d"], as_index=False)[["lula_t2", "flavio_t2"]].sum()
    g["lula"] = g.lula_t2 > g.flavio_t2
    uf = z.groupby("uf")[["lula_t2", "flavio_t2"]].sum()
    uf_lula = uf.lula_t2 > uf.flavio_t2
    dist_l = g.groupby("uf").lula.sum()
    out = {"dist_lula": dist_l.to_dict(), "uf_lula": uf_lula.to_dict(), "desvio": 0.0}
    tot = z.groupby(["uf", "d"]).peso.sum()
    quota = tot.groupby("uf").mean()
    out["desvio"] = float(((tot / quota.reindex(tot.index.get_level_values(0)).values) - 1).abs().max())
    l_dist = int(dist_l.sum())
    l_bonus = sum(SENADORES for u, v in uf_lula.items() if v)
    out["lula_distritos_puro"] = l_dist
    out["lula_distritos_bonus"] = l_dist + l_bonus
    return out


def main() -> None:
    z = carregar()
    rng = np.random.default_rng(SEMENTE)
    uf = z.groupby("uf")[["lula_t2", "flavio_t2"]].sum()
    uf["pct"] = uf.lula_t2 / (uf.lula_t2 + uf.flavio_t2) * 100
    uf["venceu_lula"] = uf.lula_t2 > uf.flavio_t2
    cad = pd.Series(CADEIRAS)
    deleg = cad + SENADORES
    total_deleg = int(deleg.sum()); maioria = total_deleg // 2 + 1
    regras = {
        "vencedor_leva": int(deleg[uf.venceu_lula].sum()),
        "proporcional_uf": float((deleg * uf.pct / 100).sum()),
    }
    base = placar(z, distritos(z, rng, 0.0))
    regras["distritos_bonus"] = base["lula_distritos_bonus"]
    regras["distritos_puro"] = base["lula_distritos_puro"]
    # sorteios do eixo de corte
    sd, sp = [], []
    desv = []
    for _ in range(SORTEIOS):
        p = placar(z, distritos(z, rng, 25.0))
        sd.append(p["lula_distritos_bonus"]); sp.append(p["lula_distritos_puro"]); desv.append(p["desvio"])
    sd, sp = np.array(sd), np.array(sp)
    # quanto cada UF varia
    por_uf = []
    ufs_sorteio = {u: [] for u in CADEIRAS}
    rng2 = np.random.default_rng(SEMENTE + 1)
    for _ in range(120):
        p = placar(z, distritos(z, rng2, 25.0))
        for u in CADEIRAS:
            ufs_sorteio[u].append(p["dist_lula"].get(u, 0))
    for u in sorted(CADEIRAS, key=lambda u: -CADEIRAS[u]):
        a = ufs_sorteio[u]
        por_uf.append({"uf": u, "cadeiras": CADEIRAS[u], "delegados": int(deleg[u]), "lula_pct": round(float(uf.pct[u]), 2), "vence": "Lula" if uf.venceu_lula[u] else "Flávio",
                       "dist_lula": int(base["dist_lula"].get(u, 0)), "dist_flavio": CADEIRAS[u] - int(base["dist_lula"].get(u, 0)), "dist_lula_min": int(min(a)), "dist_lula_max": int(max(a)),
                       "eleitores": int(uf.lula_t2[u] + uf.flavio_t2[u])})
    # histograma
    def hist(v):
        vs, cs = np.unique(v, return_counts=True)
        return [{"lula": int(a), "n": int(b)} for a, b in zip(vs, cs)]
    nac_l, nac_f = int(uf.lula_t2.sum()), int(uf.flavio_t2.sum())
    saida = {
        "total_delegados": total_deleg, "maioria": maioria, "cadeiras": int(cad.sum()), "senadores_por_uf": SENADORES, "sorteios": SORTEIOS,
        "popular": {"lula": nac_l, "flavio": nac_f, "lula_pct": round(nac_l / (nac_l + nac_f) * 100, 2)},
        "regras": {"vencedor_leva": regras["vencedor_leva"], "proporcional_uf": round(regras["proporcional_uf"], 1), "distritos_bonus": regras["distritos_bonus"], "distritos_puro": regras["distritos_puro"]},
        "faixa": {"distritos_bonus": {"min": int(sd.min()), "p5": int(np.percentile(sd, 5)), "mediana": int(np.median(sd)), "p95": int(np.percentile(sd, 95)), "max": int(sd.max()), "prob_lula": round(float((sd >= maioria).mean()), 3), "hist": hist(sd)},
                  "distritos_puro": {"min": int(sp.min()), "p5": int(np.percentile(sp, 5)), "mediana": int(np.median(sp)), "p95": int(np.percentile(sp, 95)), "max": int(sp.max()), "prob_lula": round(float((sp >= 257).mean()), 3), "hist": hist(sp)}},
        "maioria_puro": 257, "desvio_max_populacao": round(float(np.mean(desv)), 3), "por_uf": por_uf,
        "ufs_venceu_lula": int(uf.venceu_lula.sum()), "ufs_venceu_flavio": int((~uf.venceu_lula).sum()),
        "exterior_ignorado": int(pd.read_csv("datasets/tse-presidente-zona-2026.csv").query("uf=='ZZ'").validos_t2.sum()),
    }
    json.dump(saida, open("modelos/colegio-eleitoral.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: saida[k] for k in ("popular", "regras", "desvio_max_populacao")}, ensure_ascii=False))
    print({k: {kk: v for kk, v in f.items() if kk != "hist"} for k, f in saida["faixa"].items()})


if __name__ == "__main__":
    main()

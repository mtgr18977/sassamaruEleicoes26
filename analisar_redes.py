"""Agrega os posts do Bluesky sobre Lula e Flávio (coletar_redes.py) em números que podem ir para o git: datasets/redes/agregado-bluesky.json.

  python analisar_redes.py
Lê o cache local de posts (datasets/redes/bluesky-bruto.jsonl, fora do git), a série de volume (bluesky-volume.csv), os rótulos da amostra (rotulos-amostra.csv)
e a avaliação dos classificadores (avaliacao-modelos.json). Sai: volume por hora, efeito do debate, hashtags, repetição de textos, composição da amostra e posição
(favorável/desfavorável/neutro) por candidato antes × depois do debate, com intervalo de confiança de Wilson (95%).
O Bluesky não é amostra do eleitorado (ver a página Redes sociais): isto mede a conversa nesta rede, não a intenção de voto.
ponytail: cada janela de coleta é uma amostra dos posts mais recentes dela; o volume vem do total que a busca informa (pode ser aproximado)."""
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone

import pandas as pd

D = "datasets/redes/"
BRT = timezone(timedelta(hours=-3))
DEBATE_INI = datetime(2026, 10, 18, 20, tzinfo=BRT)
DEBATE_FIM = datetime(2026, 10, 18, 22, tzinfo=BRT)


def wilson(k, n, z=1.96):
    """Intervalo de Wilson para uma proporção (em %)."""
    if n == 0:
        return None
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(100 * max(0, c - h), 1), round(100 * min(1, c + h), 1)]


def volume():
    v = pd.read_csv(D + "bluesky-volume.csv")
    v["ini"], v["fim_dt"] = pd.to_datetime(v.inicio, format="ISO8601", utc=True), pd.to_datetime(v.fim, format="ISO8601", utc=True)
    v = v[v.fim_dt == v.groupby(["inicio", "candidato"]).fim_dt.transform("max")]            # a última janela pode ter sido coletada mais de uma vez: fica a mais recente
    v["horas"] = (v.fim_dt - v.ini).dt.total_seconds() / 3600
    p = v.pivot_table(index=["inicio", "fim", "horas"], columns="candidato", values="posts", aggfunc="first").reset_index().dropna()
    p = p.sort_values("inicio")
    out = [dict(ini=r.inicio, fim=r.fim, horas=round(r.horas, 2), lula=int(r.lula), flavio=int(r.flavio), lula_ph=round(r.lula / r.horas, 1), flavio_ph=round(r.flavio / r.horas, 1)) for r in p.itertuples()]
    return out


def efeito_debate(vol):
    """Compara cada hora do debate com o volume normal DA MESMA FAIXA DO DIA (0-6h, 6-12h, 12-18h, 18-24h): mediana das janelas de 6 h dos dias 12 a 17/10.
    O volume tem ciclo diário forte (à noite cai, à tarde e à noite sobe); comparar com a mediana geral exageraria o efeito do debate."""
    ini = lambda s: datetime.fromisoformat(s).astimezone(BRT)
    faixa = lambda dt: dt.hour // 6 * 6
    base = {}
    for w in vol:
        a = ini(w["ini"])
        if w["horas"] >= 5 and a < datetime(2026, 10, 18, tzinfo=BRT):
            for c in ("lula", "flavio"):
                base.setdefault((faixa(a), c), []).append(w[c + "_ph"])
    med = {k: float(pd.Series(v).median()) for k, v in base.items()}
    horas = [w for w in vol if DEBATE_INI - timedelta(hours=1) <= ini(w["ini"]) < DEBATE_FIM + timedelta(hours=6) and w["horas"] <= 1.01]
    out = []
    for w in horas:
        a = ini(w["ini"])
        bl, bf = med[(faixa(a), "lula")], med[(faixa(a), "flavio")]
        out.append(dict(h=a.strftime("%d/%m %Hh"), lula_ph=w["lula_ph"], flavio_ph=w["flavio_ph"], lula_base=round(bl, 1), flavio_base=round(bf, 1), lula_x=round(w["lula_ph"] / bl, 2), flavio_x=round(w["flavio_ph"] / bf, 2)))
    return dict(base_por_faixa={f"{f:02d}h-{f + 6:02d}h": {c: round(med[(f, c)], 1) for c in ("lula", "flavio")} for f in (0, 6, 12, 18) if (f, "lula") in med}, horas=out)


def corpus(d):
    um = lambda c: int(((d.ml if c == "lula" else d.mf) & ~(d.mf if c == "lula" else d.ml)).sum())
    ac = d.autor.value_counts()
    rep = d.norm[d.norm.duplicated(keep=False) & (d.norm.str.len() > 20)].value_counts()
    return dict(posts=int(len(d)), autores=int(d.autor.nunique()), so_lula=um("lula"), so_flavio=um("flavio"), ambos=int((d.ml & d.mf).sum()), nenhum=int((~d.ml & ~d.mf).sum()),
                texto_repetido_pct=round(100 * float(d.norm.duplicated().mean()), 1), com_link_pct=round(100 * float(d.link.mean()), 1),
                autores_10mais_posts=int((ac >= 10).sum()), posts_dos_autores_10mais_pct=round(100 * float(ac[ac >= 10].sum() / len(d)), 1),
                textos_repetidos_5x=int((rep >= 5).sum()), posts_em_textos_repetidos_5x=int(rep[rep >= 5].sum()),
                de=d.t.min().strftime("%d/%m/%Y"), ate=d.t.max().strftime("%d/%m/%Y %Hh%M"))


def hashtags(d):
    tag = re.compile(r"#[\wÀ-ÿ]+", re.I)
    out = {}
    for nome, sel in (("antes", d.t < DEBATE_INI), ("depois", d.t >= DEBATE_INI)):
        c = Counter()
        for tx in d[sel].texto:
            c.update({unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode() for t in tag.findall(tx)})   # sem acento: #abreosigiloflavio = #abreosigiloflávio
        out[nome] = dict(posts=int(sel.sum()), top=[[k, int(n)] for k, n in c.most_common(12)])
    return out


def posicao(rot):
    out = []
    for cand in ("lula", "flavio"):
        for deb, nome in ((False, "antes do debate"), (True, "debate e depois")):
            g = rot[(rot.cand == cand) & (rot.debate == deb)]
            n = len(g)
            c = g.rotulo.value_counts().to_dict()
            out.append(dict(candidato=cand, periodo=nome, n=int(n), **{k: dict(n=int(c.get(k, 0)), pct=round(100 * c.get(k, 0) / n, 1), ic=wilson(c.get(k, 0), n)) for k in ("P", "N", "0")}))
    return out


def main():
    d = pd.DataFrame([json.loads(l) for l in open(D + "bluesky-bruto.jsonl", encoding="utf-8")])
    d["t"] = pd.to_datetime(d.criado, utc=True).dt.tz_convert("America/Sao_Paulo")
    d["ml"] = d.texto.str.contains(r"\blula\b", case=False, regex=True)
    d["mf"] = d.texto.str.contains(r"fl[áa]vio", case=False, regex=True)
    d["norm"] = d.texto.str.lower().str.replace(r"https?://\S+", "", regex=True).str.replace(r"\W+", " ", regex=True).str.strip()
    vol = volume()
    rot = pd.read_csv(D + "rotulos-amostra.csv")
    out = dict(gerado_em=datetime.now(BRT).strftime("%d/%m/%Y %Hh%M"), debate="18/10/2026, 20h às 22h (Band)", volume=vol, debate_efeito=efeito_debate(vol), corpus=corpus(d), hashtags=hashtags(d),
               posicao=posicao(rot), amostra_rotulada=int(len(rot)), avaliacao=json.load(open(D + "avaliacao-modelos.json", encoding="utf-8")))
    json.dump(out, open(D + "agregado-bluesky.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("grava", D + "agregado-bluesky.json")
    print(json.dumps({k: out[k] for k in ("debate_efeito", "corpus", "hashtags")}, ensure_ascii=False)[:2600])
    for p in out["posicao"]:
        print(p["candidato"], p["periodo"], p["n"], {k: (p[k]["pct"], p[k]["ic"]) for k in ("P", "N", "0")})


if __name__ == "__main__":
    main()

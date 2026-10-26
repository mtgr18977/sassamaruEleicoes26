"""Sorteia os posts do Bluesky que eu vou ler e classificar (a favor, contra ou neutro) para um período do cache local.

  python amostrar_redes.py globo SAIDA.jsonl [n_por_grupo]
Regras (as mesmas da amostra do debate da Band): só posts que citam um candidato (Lula ou Flávio, não os dois), sem link, sem texto repetido no cache,
no máximo 3 por autor por dia, n por grupo sorteados (semente fixa). Período "globo": a partir de 23/10 21h20; "resultado": a partir de 25/10 18h (apuração). Grava id, candidato e texto em SAIDA
(arquivo LOCAL, fora do git: os textos não vão para o repositório). Depois eu leio e gravo só id, candidato, período e rótulo em datasets/redes/rotulos-amostra.csv."""
import json
import sys

import pandas as pd

from analisar_redes import APURACAO_INI, D, GLOBO_INI

periodo, saida = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 76
assert periodo in ("globo", "resultado")
INICIO = GLOBO_INI if periodo == "globo" else APURACAO_INI
d = pd.DataFrame([json.loads(l) for l in open(D + "bluesky-bruto.jsonl", encoding="utf-8")])
d["t"] = pd.to_datetime(d.criado, utc=True).dt.tz_convert("America/Sao_Paulo")
d["ml"] = d.texto.str.contains(r"\blula\b", case=False, regex=True)
d["mf"] = d.texto.str.contains(r"fl[áa]vio", case=False, regex=True)
d["norm"] = d.texto.str.lower().str.replace(r"https?://\S+", "", regex=True).str.replace(r"\W+", " ", regex=True).str.strip()
d = d[(d.t >= INICIO) & ~d.link & ~d.norm.duplicated(keep=False)]
d["dia"] = d.t.dt.date
d = d.sample(frac=1, random_state=2026)
d = d[d.groupby(["autor", "dia"]).cumcount() < 3]
out = []
for cand, sel in (("lula", d.ml & ~d.mf), ("flavio", d.mf & ~d.ml)):
    g = d[sel].head(n)
    print(cand, "elegíveis:", int(sel.sum()), "sorteados:", len(g))
    out += [dict(id=r.id, cand=cand, texto=r.texto) for r in g.itertuples()]
with open(saida, "w", encoding="utf-8") as f:
    f.write("\n".join(json.dumps(x, ensure_ascii=False) for x in out) + "\n")

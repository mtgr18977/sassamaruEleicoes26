"""Compara o resultado do 2º turno de 2026 (datasets/resultado-2026-turno2.csv) com o que o modelo e as pesquisas projetavam.

  python avaliar_2turno.py
Resultado nacional e por UF: Lula/(Lula+Flávio) nos votos válidos. Os números de 25/10 vêm de matérias que reproduzem o painel do TSE (Wikipedia, g1, CGN), com 99,9% das seções;
o arquivo oficial de votação do TSE (cdn.tse.jus.br) ainda não tinha o 2º turno quando isto foi feito. Troque datasets/resultado-2026-turno2.csv pelo oficial quando sair.
Sai: modelos/avaliacao-2turno.json (resumo, tabela por instituto e por UF) e as tabelas no terminal.
Compara: (1) o modelo (modelos/parametros.json e previsao-uf-turno2.csv), (2) a última pesquisa de cada instituto (as mesmas que o modelo usa, via pesquisas.preparar),
(3) o erro de cada instituto no 1º turno (erros_1turno.py)."""
import json
import math

import numpy as np
import pandas as pd

import erros_1turno
from pesquisas import INICIO_2T, preparar

D = "datasets/"
res = pd.read_csv(D + "resultado-2026-turno2.csv").set_index("uf")
REAL = float(res.loc["BR", "lula_pct"])
param = json.load(open("modelos/parametros.json", encoding="utf-8"))
t2 = param["turno2"]
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
logit = lambda p: math.log(p / (1 - p))

# ---- nacional
modelo = 100 * t2["p_pesquisas"]
sd = t2["sd_logit"]
lo, hi = [100 / (1 + math.exp(-(logit(t2["p_pesquisas"]) + s * 1.645 * sd))) for s in (-1, 1)]
nac = dict(real=REAL, modelo=round(modelo, 2), erro_modelo=round(modelo - REAL, 2), faixa90=[round(lo, 1), round(hi, 1)], dentro_faixa90=bool(lo <= REAL <= hi),
           z=round((logit(modelo / 100) - logit(REAL / 100)) / sd, 2), chance_lula_modelo=round(100 * Phi(logit(t2["p_pesquisas"]) / sd), 1))

# ---- por instituto
d = preparar()
x = d.dropna(subset=["p2"])
x = x[x.campo_fim >= INICIO_2T].sort_values("campo_fim")
x["s"] = 100 * x.p2
ult = x.groupby("instituto").tail(1).set_index("instituto")
t = pd.DataFrame({"campo_fim": ult.campo_fim.dt.strftime("%d/%m"), "n": ult.n.astype(int), "ultima": ult.s.round(2)})
t["erro_2t"] = (t.ultima - REAL).round(2)
t["erro_1t"] = erros_1turno.erros().reindex(t.index)
t = t.sort_values("erro_2t")
inst = dict(media_simples=round(float(t.ultima.mean()), 2), mediana=round(float(t.ultima.median()), 2), erro_media=round(float(t.ultima.mean() - REAL), 2),
            todas_abaixo_do_real=bool((t.ultima < REAL).all()), melhor=t.erro_2t.abs().idxmin(), pior=t.erro_2t.abs().idxmax(),
            erro_1t_medio=round(float(t.erro_1t.mean()), 2), erro_2t_medio=round(float(t.erro_2t.mean()), 2),
            corr_erro_1t_2t=round(float(t.dropna(subset=["erro_1t"]).erro_1t.corr(t.dropna(subset=["erro_1t"]).erro_2t)), 2))

# ---- por UF
m = pd.read_csv("modelos/previsao-uf-turno2.csv").set_index("uf")
w = pd.Series({u["uf"]: u["validos"] for u in param["mc"]["turno2"]["unidades"]})
b = pd.Series({u["uf"]: 100 * u["pbase"] for u in param["mc"]["turno2"]["unidades"]})
act = res.drop(index="BR").lula_pct
u = pd.DataFrame({"real": act, "modelo": m.mediana, "p5": m.p5, "p95": m.p95, "base_1t_2026": b}).dropna()
u["erro"] = (u.modelo - u.real).round(2)
u["dentro90"] = (u.real >= u.p5) & (u.real <= u.p95)
u["vencedor_certo"] = (u.modelo > 50) == (u.real > 50)
ww = w.reindex(u.index)
uf = dict(n=int(len(u)), mae=round(float(u.erro.abs().mean()), 2), vies=round(float(u.erro.mean()), 2), vies_ponderado=round(float(np.average(u.erro, weights=ww)), 2),
          desvio_apos_tirar_o_vies=round(float((u.erro - u.erro.mean()).std()), 2), corr=round(float(np.corrcoef(u.modelo, u.real)[0, 1]), 3),
          dentro_90=int(u.dentro90.sum()), vencedor_certo=int(u.vencedor_certo.sum()), errou_vencedor=u.index[~u.vencedor_certo].tolist(),
          maior_erro=u.erro.abs().idxmax(), menor_erro=u.erro.abs().idxmin())

out = dict(fonte="datasets/resultado-2026-turno2.csv (provisório: painel do TSE via imprensa, 99,9% das seções)", nacional=nac, institutos=inst, uf_resumo=uf,
           tabela_institutos=t.reset_index().rename(columns={"index": "instituto"}).to_dict("records"),
           tabela_uf=u.round(2).reset_index().to_dict("records"))
json.dump(out, open("modelos/avaliacao-2turno.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print("NACIONAL", nac, "\nINSTITUTOS", inst, "\nUF", uf)
print(t.to_string())
print(u.sort_values("erro").round(2).to_string())

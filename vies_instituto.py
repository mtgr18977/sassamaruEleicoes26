"""Teste (não altera o modelo): e se cada instituto carregasse o erro que teve no 1º turno de 2026?

Erro do instituto = Lula/(Lula+Flávio) da última pesquisa antes do 1º turno − resultado (48,99%). Esse erro é descontado das pesquisas de 2º turno do mesmo
instituto (inteiro, pela metade ou só para a Vox) e a estimativa do 2º turno (pesquisas.estimar) é refeita. Compara também com o erro persistente em 2022.
  python vies_instituto.py
ponytail: 1 pesquisa final por instituto = 1 observação; erro do 1º turno (inclui a migração dos "demais") não é necessariamente erro do 2º."""
import math

import numpy as np
import pandas as pd

from pesquisas import HOJE, HORIZONTE, P2022, SD_PISO_2T_PP, estimar, logit, preparar, vies_rmse

D = "datasets/"
Phi = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
br = pd.read_csv(D + "resultado-2026-turno1.csv").query("uf == 'BR'").iloc[0]
real = 100 * br.votos_lula / (br.votos_lula + br.votos_flavio)

d = preparar()
fin = d[d.campo_fim <= "2026-10-03"].dropna(subset=["p1s"]).sort_values("campo_fim")
ult = fin.groupby("instituto").tail(1).set_index("instituto")
erro = (100 * ult.p1s - real).round(2)                      # + = deu a Lula mais do que ele teve
print("Erro da última pesquisa do 1º turno (p.p. em Lula/(Lula+Flávio); resultado %.2f%%)" % real)
print(erro.sort_values().to_string(), "\n")

sv, _ = vies_rmse(2)


def refazer(desc, nome):
    x = d.copy()
    x["p2"] = x.p2 - x.instituto.map(desc).fillna(0) / 100
    p, sd, h, n = estimar(x, "p2", hoje=HOJE, sd_vies=sv, h_dias=HORIZONTE[2], piso_pp=SD_PISO_2T_PP)
    return dict(cenario=nome, s2=round(100 * p, 2), lo=round(100 * 1 / (1 + math.exp(-(logit(p) - 1.645 * sd))), 1), hi=round(100 * 1 / (1 + math.exp(-(logit(p) + 1.645 * sd))), 1), chance_lula=round(100 * Phi(logit(p) / sd), 1))


linhas = [refazer({}, "Base (sem correção, o que o site usa)"),
          refazer(erro.to_dict(), "Cada instituto − seu erro inteiro (1×)"),
          refazer((erro / 2).to_dict(), "Cada instituto − metade do erro (0,5×)"),
          refazer({"Vox Brasil": 0.0, **{i: e for i, e in erro.items() if i != "Vox Brasil"}}, "Todos − erro, Vox sem correção"),
          refazer({i: erro.mean() for i in erro.index}, "Todos − o erro médio (%.1f p.p.)" % erro.mean())]
t = pd.DataFrame(linhas)
t["delta_s2"] = (t.s2 - t.s2[0]).round(2); t["delta_chance"] = (t.chance_lula - t.chance_lula[0]).round(1)
print(t.to_string(index=False), "\n")

# o erro do instituto persiste? 2022 (vies-pesquisas.csv) × 2026, 1º turno
v = pd.read_csv(D + "vies-pesquisas.csv").query("turno == 1 and ano == 2022")
n22 = pd.read_csv(D + "tse-presidente-nacional.csv").set_index(["ano", "turno"]).loc[(2022, 1)]
r22 = 100 * n22.votos_pt / (n22.votos_pt + n22.votos_antipt)
e22 = (100 * v.pt / (v.pt + v.rival) - r22).set_axis(v.instituto)
c = pd.DataFrame({"erro_2022": e22.round(2), "erro_2026": erro}).dropna()
print("Erro de cada instituto no 1º turno: 2022 × 2026 (p.p.)"); print(c.to_string())
if len(c) > 2:
    print("correlação (n=%d): %.2f" % (len(c), np.corrcoef(c.erro_2022, c.erro_2026)[0, 1]))

"""Compara o resultado do 2º turno de 2026 (datasets/resultado-2026-turno2.csv) com o que o modelo e as pesquisas projetavam.

  python avaliar_2turno.py
Resultado nacional e por UF: Lula/(Lula+Flávio) nos votos válidos. O resultado é o OFICIAL do TSE (portal resultados.tse.jus.br, 100% das seções, 25/10/2026 23h27), baixado por fetch_tse_2turno.py em datasets/resultado-2026-turno2.csv;
os arquivos de votação por zona/seção (dados abertos, cdn.tse.jus.br) ainda não tinham o 2º turno quando isto foi feito.
Sai: modelos/avaliacao-2turno.json (resumo, tabela por instituto e por UF) e as tabelas no terminal.
Compara: (1) o modelo (modelos/parametros.json e previsao-uf-turno2.csv), (2) a última pesquisa de cada instituto (as mesmas que o modelo usa, via pesquisas.preparar),
(3) o erro de cada instituto no 1º turno (erros_1turno.py)."""
import json
import math

import numpy as np
import pandas as pd

import erros_1turno
from pesquisas import INICIO_2T, P2022, evolucao, preparar, vies_eleicao

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
act = res.drop(index=["BR", "ZZ"]).lula_pct                      # as 27 UFs; o exterior (ZZ) vai à parte
u = pd.DataFrame({"real": act, "modelo": m.mediana, "p5": m.p5, "p95": m.p95, "base_1t_2026": b}).dropna()
u["erro"] = (u.modelo - u.real).round(2)
u["dentro90"] = (u.real >= u.p5) & (u.real <= u.p95)
u["vencedor_certo"] = (u.modelo > 50) == (u.real > 50)
ww = w.reindex(u.index)
uf = dict(n=int(len(u)), mae=round(float(u.erro.abs().mean()), 2), vies=round(float(u.erro.mean()), 2), vies_ponderado=round(float(np.average(u.erro, weights=ww)), 2),
          desvio_apos_tirar_o_vies=round(float((u.erro - u.erro.mean()).std()), 2), corr=round(float(np.corrcoef(u.modelo, u.real)[0, 1]), 3),
          dentro_90=int(u.dentro90.sum()), vencedor_certo=int(u.vencedor_certo.sum()), errou_vencedor=u.index[~u.vencedor_certo].tolist(),
          maior_erro=u.erro.abs().idxmax(), menor_erro=u.erro.abs().idxmin())

# ---- réguas: o que cada "previsão" simples teria dito (erro = previsão − resultado; negativo = subestimou Lula)
vm = vies_eleicao(2)[0]
p1t = float(erros_1turno.resultado()[0])
reguas = [("Modelo publicado em 25/10 (nível sem tendência)", modelo), ("Modelo até 24/10 (com tendência linear)", 49.45),
          ("Média simples da última pesquisa de cada instituto", inst["media_simples"]), ("Modelo com ½ do viés histórico descontado", modelo - vm / 2),
          ("Modelo com o viés histórico descontado (−%.2f p.p.)" % vm, modelo - vm), ("Repetir o 1º turno de 2026 (Lula/(Lula+Flávio) = %.2f%%)" % p1t, p1t),
          ("Repetir o 2º turno de 2022 (%.2f%%)" % (100 * P2022[2]), 100 * P2022[2])]
reguas = [dict(nome=n.replace(".", ","), previsao=round(v, 2), erro=round(v - REAL, 2)) for n, v in reguas]

# ---- linha do tempo: o modelo (metodologia final) reconstruído data a data e a chance de Lula implícita
datas = [str(x.date()) for x in pd.date_range("2026-10-14", "2026-10-25", freq="D")]
tempo = [dict(data=e["data"], s2=round(100 * e["s2"], 2), chance=round(100 * Phi(logit(e["s2"]) / e["sd2"]), 1), n2=e["n2"]) for e in evolucao(datas)]

# ---- o que o site mostrou a cada versão (do HANDOFF.md e dos PRs)
versoes = [dict(data="21/10", pr="#31/#33", s2=48.37, chance=25.7, nota="44 pesquisas de 2º turno (24 eram cenários hipotéticos de antes do 1º turno), com tendência"),
           dict(data="22/10", pr="#34", s2=48.43, chance=26.5, nota="Veritá/CNN entra; erros de 1º turno de 16 institutos"),
           dict(data="22/10", pr="#35", s2=49.46, chance=41.4, nota="só pesquisas feitas depois do 1º turno (a campanha mudou)"),
           dict(data="24/10", pr="#37", s2=49.45, chance=41.3, nota="9 pesquisas de véspera (Datafolha ×2, Quaest, Atlas, Nexus, Palver, Vox, CNT/MDA, Colectta)"),
           dict(data="25/10", pr="#38", s2=49.03, chance=34.9, nota="entram Real Time Big Data, Alfa, Ipespe e rodadas novas de Futura, Gerp e Veritá; sai a tendência linear")]
for v in versoes:
    v["erro"] = round(v["s2"] - REAL, 2)

# ---- incongruências medidas
# (1) efeito de cada instituto, em p.p. de Lula/(Lula+Flávio) (o modelo guarda em logit; 1 p.p. ≈ 0,04 logit perto de 50%)
base = t2["p_pesquisas"]
efeitos = sorted([dict(instituto=k, pp=round(100 * (1 / (1 + math.exp(-(logit(base) + v))) - base), 2)) for k, v in t2["house_effects_logit"].items()], key=lambda e: e["pp"])
# (2) o modelo calcula a parcela dos TOTAIS; estes são os válidos que os institutos publicaram (matérias lidas; só as pesquisas em que as duas coisas existem)
PUB = {("Datafolha", "2026-10-22"): 50.0, ("Datafolha", "2026-10-24"): 49.0, ("Quaest", "2026-10-24"): 49.0, ("AtlasIntel", "2026-10-23"): 49.2, ("Nexus/BTG", "2026-10-24"): 49.5,
       ("CNT/MDA", "2026-10-23"): 49.3, ("Colectta", "2026-10-23"): 50.3, ("Veritá", "2026-10-23"): 48.44, ("Alfa Inteligência", "2026-10-19"): 48.5,
       ("RealTimeBigData", "2026-10-22"): 48.0, ("RealTimeBigData", "2026-10-19"): 48.0, ("Ipespe/Abrapel", "2026-10-15"): 48.8}
arred = []
for (i, f), v in PUB.items():
    r = x[(x.instituto == i) & (x.campo_fim == f)]
    arred.append(dict(instituto=i, campo_fim=pd.Timestamp(f).strftime("%d/%m"), totais=round(float(r.s.iloc[0]), 2), publicado=v, dif=round(float(r.s.iloc[0]) - v, 2)))
arred_res = dict(n=len(arred), media_abs=round(float(np.mean([abs(r["dif"]) for r in arred])), 2), max_abs=round(float(max(abs(r["dif"]) for r in arred)), 2), media=round(float(np.mean([r["dif"] for r in arred])), 2))
# (3) quanto cada instituto, sozinho, mexe no nível (sensibilidade-2t.csv, linhas "Sem …")
sens = pd.read_csv("modelos/sensibilidade-2t.csv")
sem = sens[sens.cenario.str.startswith("Sem ")]
sem_res = dict(max_mudanca=round(float(sem.delta_s2.abs().max()), 2), instituto=sem.loc[sem.delta_s2.abs().idxmax(), "cenario"][4:],
               max_mudanca_chance=round(float(sem.delta_chance.abs().max()), 1))

# ---- 1º × 2º turno com os arquivos oficiais do portal do TSE (fetch_tse_2turno.py, com e sem --turno1): a conta de votos e o comparecimento por UF
t1 = pd.read_csv(D + "tse-presidente-1turno-uf.csv").set_index("uf")
t2u = pd.read_csv(D + "tse-presidente-2turno-uf.csv").set_index("uf")
c = pd.DataFrame(index=t1.index)
c["d_lula"], c["d_flavio"] = t2u.votos_lula - t1.votos_lula, t2u.votos_flavio - t1.votos_flavio
c["outros"], c["d_bn"], c["d_comp"] = t1.votos_outros, (t1.brancos + t1.nulos) - (t2u.brancos + t2u.nulos), t2u.comparecimento - t1.comparecimento
c["residuo"] = c.outros + c.d_bn + c.d_comp - c.d_lula - c.d_flavio
c["lula_1t"] = 100 * t1.votos_lula / (t1.votos_lula + t1.votos_flavio)
c["lula_2t"] = 100 * t2u.votos_lula / (t2u.votos_lula + t2u.votos_flavio)
c["swing"] = c.lula_2t - c.lula_1t
c["d_comp_pp"] = 100 * (t2u.comparecimento / t2u.eleitorado - t1.comparecimento / t1.eleitorado)
n = c.loc["BR"]
cont = dict(lula_1t=int(t1.loc["BR", "votos_lula"]), lula_2t=int(t2u.loc["BR", "votos_lula"]), flavio_1t=int(t1.loc["BR", "votos_flavio"]), flavio_2t=int(t2u.loc["BR", "votos_flavio"]),
            outros_1t=int(n.outros), queda_branco_nulo=int(n.d_bn), mais_comparecimento=int(n.d_comp), ganho_lula=int(n.d_lula), ganho_flavio=int(n.d_flavio),
            abstencao_1t=int(t1.loc["BR", "abstencao"]), abstencao_2t=int(t2u.loc["BR", "abstencao"]), residuo=int(n.residuo), swing_nacional=round(float(n.swing), 2), d_comp_pp=round(float(n.d_comp_pp), 2))
cu = c.drop(index=["BR", "ZZ"])
erro_uf = u.erro
cu = cu.join(erro_uf.rename("erro_modelo"))
teste = dict(swing_medio=round(float(cu.swing.mean()), 2), swing_dp=round(float(cu.swing.std()), 2), swing_min=round(float(cu.swing.min()), 2), uf_swing_min=cu.swing.idxmin(), swing_max=round(float(cu.swing.max()), 2), uf_swing_max=cu.swing.idxmax(),
             ufs_com_swing_positivo=int((cu.swing > 0).sum()), ufs_com_queda_de_comparecimento=int((cu.d_comp < 0).sum()), ufs_queda=cu.index[cu.d_comp < 0].tolist(),
             corr_comparecimento_erro=round(float(cu.d_comp_pp.corr(cu.erro_modelo)), 2), corr_comparecimento_swing=round(float(cu.d_comp_pp.corr(cu.swing)), 2),
             residuo_max_uf=int(cu.residuo.abs().max()))
uf_turnos = cu.reset_index().rename(columns={"uf": "uf"})[["uf", "lula_1t", "lula_2t", "swing", "d_comp_pp", "erro_modelo"]].round(2).to_dict("records")

# ---- a mesma conta de votos nas eleições de 2002 a 2022 (tse-presidente-nacional.csv): ganho dos dois finalistas = outros + queda de branco/nulo + mais comparecimento
nac_h = pd.read_csv(D + "tse-presidente-nacional.csv").set_index(["ano", "turno"])
hist = []
for ano in (2002, 2006, 2010, 2014, 2018, 2022):
    p1, p2 = nac_h.loc[(ano, 1)], nac_h.loc[(ano, 2)]
    hist.append(dict(ano=ano, outros=round(p1.votos_outros / 1e6, 2), queda_bn=round(((p1.brancos + p1.nulos) - (p2.brancos + p2.nulos)) / 1e6, 2), mais_comp=round((p2.comparecimento - p1.comparecimento) / 1e6, 2),
                     ganho_pt=round((p2.votos_pt - p1.votos_pt) / 1e6, 2), ganho_anti=round((p2.votos_antipt - p1.votos_antipt) / 1e6, 2)))
hist.append(dict(ano=2026, outros=round(cont["outros_1t"] / 1e6, 2), queda_bn=round(cont["queda_branco_nulo"] / 1e6, 2), mais_comp=round(cont["mais_comparecimento"] / 1e6, 2),
                 ganho_pt=round(cont["ganho_lula"] / 1e6, 2), ganho_anti=round(cont["ganho_flavio"] / 1e6, 2)))

# ---- regiões
REG = {"Nordeste": "AL BA CE MA PB PE PI RN SE", "Norte": "AC AM AP PA RO RR TO", "Centro-Oeste": "DF GO MS MT", "Sudeste": "ES MG RJ SP", "Sul": "PR RS SC"}
regioes = [dict(regiao=k, ufs=len(v.split()), real=round(float(u.loc[v.split()].real.mean()), 1), erro=round(float(u.loc[v.split()].erro.mean()), 2)) for k, v in REG.items()]

zz = m.loc["ZZ"] if "ZZ" in m.index and "ZZ" in res.index else None
exterior = None if zz is None else dict(previsto=round(float(zz.mediana), 2), real=round(float(res.loc["ZZ", "lula_pct"]), 2), erro=round(float(zz.mediana - res.loc["ZZ", "lula_pct"]), 2), p5=round(float(zz.p5), 1), p95=round(float(zz.p95), 1))
out = dict(exterior=exterior, fonte="datasets/resultado-2026-turno2.csv (oficial: portal de resultados do TSE, 100% das seções, 25/10/2026 23h27)", nacional=nac, reguas=reguas, linha_do_tempo=tempo, versoes=versoes, regioes=regioes, contabilidade=cont, historico_conta=hist, teste_comparecimento=teste, uf_turnos=uf_turnos, efeitos_instituto=efeitos, arredondamento=arred, arredondamento_resumo=arred_res, sem_instituto=sem_res, institutos=inst, uf_resumo=uf,
           tabela_institutos=t.reset_index().rename(columns={"index": "instituto"}).to_dict("records"),
           tabela_uf=u.round(2).reset_index().to_dict("records"))
json.dump(out, open("modelos/avaliacao-2turno.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print("NACIONAL", nac, "\nINSTITUTOS", inst, "\nUF", uf)
print(t.to_string())
print(u.sort_values("erro").round(2).to_string())

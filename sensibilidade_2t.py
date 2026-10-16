"""Sensibilidade da projeção do 2º turno à confiança em cada instituto (não altera o modelo).

Cenários: (1) base, (2) correção pelo erro que cada instituto teve no 1º turno (½× e 1×), (3) peso pela acurácia no 1º turno,
(4) só os institutos que mais se aproximaram (Palver, Gerp), (5) só pesquisas pós-1º turno (campo a partir de 5/10), com e sem a tendência linear, e (6) retirar um instituto de cada vez.
  python sensibilidade_2t.py              # imprime a tabela, grava modelos/sensibilidade-2t.csv
  python sensibilidade_2t.py --grafico X  # também grava o gráfico em X (PNG; requer matplotlib)
Erro do 1º turno = Lula/(Lula+Flávio) da última pesquisa antes de 4/10 − resultado (48,99%); + = deu a Lula mais do que ele teve.
ponytail: 1 pesquisa por instituto = 1 observação; PoderData, Nexus/BTG e Futura não têm pesquisa de 1º turno no CSV e ficam sem correção/peso extra;
o erro do 1º turno mistura a migração dos "demais"; a tendência linear do modelo, com janela curta, extrapola o último trecho (ver "só pós-1º turno"); Palver e Gerp entram pelos números da imprensa (relatórios não conferidos)."""
import argparse
import math

import numpy as np
import pandas as pd

from pesquisas import DEFF, HOJE, HORIZONTE, SD_PISO_2T_PP, TAU_DIAS, estimar, logit, preparar, vies_rmse

D = "datasets/"
Phi = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
br = pd.read_csv(D + "resultado-2026-turno1.csv").query("uf == 'BR'").iloc[0]
REAL = 100 * br.votos_lula / (br.votos_lula + br.votos_flavio)
TAU_ACURACIA = 1.0   # ASSUMIDO (p.p.): erro mínimo efetivo no peso 1/(erro² + τ²); evita peso infinito para quem errou ~0
INICIO_2T = pd.Timestamp("2026-10-05")

d = preparar()
fin = d[d.campo_fim <= "2026-10-03"].dropna(subset=["p1s"]).sort_values("campo_fim")
erro = (100 * fin.groupby("instituto").tail(1).set_index("instituto").p1s - REAL)
erro["Palver"] = 100 * 43 / (43 + 47) - REAL          # Palver 30/9–3/10: Lula 43 × Flávio 47 (Exame, BR-00198/2026)
erro["Gerp"] = 100 * 44 / (44 + 46) - REAL            # Gerp 30/9–2/10: Lula 44 × Flávio 46 (Gazeta do Povo, BR-00509/2026)
erro = erro.round(2)
sv, _ = vies_rmse(2)
H = HORIZONTE[2]


def rodar(x, nome, direto=False, base_sd=None):
    """Estima o 2º turno em x. direto=True: média ponderada simples (poucos institutos para o ajuste de efeito de casa)."""
    if direto:
        y = x.dropna(subset=["p2"])
        y = y[y.data <= HOJE]
        dias = (y.data - HOJE).dt.days.to_numpy(float)
        w = np.exp(dias / TAU_DIAS) * y.n.to_numpy() / DEFF
        p, sd = float((w * y.p2).sum() / w.sum()), base_sd
        n = len(y)
    else:
        p, sd, _, n = estimar(x, "p2", hoje=HOJE, sd_vies=sv, h_dias=H, piso_pp=SD_PISO_2T_PP)
    lo = 100 / (1 + math.exp(-(logit(p) - 1.645 * sd)))
    hi = 100 / (1 + math.exp(-(logit(p) + 1.645 * sd)))
    return dict(cenario=nome, s2=round(100 * p, 2), lo=round(lo, 1), hi=round(hi, 1), chance_lula=round(100 * Phi(logit(p) / sd), 1), n_pesquisas=n)


def descontar(desc):
    x = d.copy()
    x["p2"] = x.p2 - x.instituto.map(desc).fillna(0) / 100
    return x


def pesar(fator):
    x = d.copy()
    x["n"] = x.n * x.instituto.map(fator).fillna(1.0)
    return x


def montar():
    base = rodar(d, "Base (o que o site usa hoje)")
    bsd = estimar(d, "p2", hoje=HOJE, sd_vies=sv, h_dias=H, piso_pp=SD_PISO_2T_PP)[1]
    w = 1 / (erro ** 2 + TAU_ACURACIA ** 2)
    w = w / w.mean()
    L = [base,
         rodar(descontar((erro / 2).to_dict()), "Cada instituto − metade do erro do 1º turno"),
         rodar(descontar(erro.to_dict()), "Cada instituto − erro inteiro do 1º turno"),
         rodar(pesar(w.to_dict()), "Peso pela acurácia no 1º turno, 1/(erro²+1²)")]
    for nome, grupo in (("Só Palver", ["Palver"]), ("Só Gerp", ["Gerp"]), ("Só Palver + Gerp", ["Palver", "Gerp"])):
        L.append(rodar(d[d.instituto.isin(grupo)], nome + " (média ponderada, sd do modelo)", direto=True, base_sd=bsd))
    pos = d[d.campo_fim >= INICIO_2T]
    L.append(rodar(pos, "Só pós-1º turno (5/10 em diante), com tendência linear"))
    L.append(rodar(pos, "Só pós-1º turno (5/10 em diante), média sem tendência", direto=True, base_sd=bsd))
    for i in sorted(d.dropna(subset=["p2"]).instituto.unique()):
        L.append(rodar(d[d.instituto != i], "Sem " + i))
    t = pd.DataFrame(L)
    t["delta_s2"] = (t.s2 - t.s2[0]).round(2)
    t["delta_chance"] = (t.chance_lula - t.chance_lula[0]).round(1)
    return t, w


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--grafico")
    a = ap.parse_args()
    t, w = montar()
    print("Erro do 1º turno (p.p. em Lula/(Lula+Flávio); resultado %.2f%%) e peso relativo pela acurácia:" % REAL)
    print(pd.DataFrame({"erro": erro, "peso": w.round(2)}).sort_values("erro").to_string(), "\n")
    print(t.to_string(index=False))
    t.to_csv("modelos/sensibilidade-2t.csv", index=False)
    if a.grafico:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        g = t.iloc[::-1].reset_index(drop=True)
        fig, ax = plt.subplots(figsize=(9, 0.34 * len(g) + 1.6))
        cores = ["#c0392b" if s < 50 else "#2c6fb7" for s in g.s2]
        ax.hlines(range(len(g)), g.lo, g.hi, color=cores, alpha=.45, lw=5)
        ax.scatter(g.s2, range(len(g)), color=cores, zorder=3)
        ax.axvline(50, color="#555", ls="--", lw=1)
        ax.axvline(t.s2[0], color="#999", ls=":", lw=1)
        ax.set_yticks(range(len(g)))
        ax.set_yticklabels([c.replace(" (média ponderada, sd do modelo)", "").replace("Só pós-1º turno (5/10 em diante), ", "Pós-1º turno: ") for c in g.cenario], fontsize=8)
        for k, r in g.iterrows():
            ax.text(max(r.hi, 53) + .3, k, "%.0f%%" % r.chance_lula, va="center", fontsize=8)
        ax.set_xlim(38, 58)
        ax.set_xlabel("Lula/(Lula+Flávio), % (ponto = estimativa; barra = faixa de 90%; número = chance de Lula)")
        ax.set_title("2º turno: sensibilidade à confiança em cada instituto (%s)" % HOJE.date().strftime("%d/%m/%Y"))
        fig.tight_layout()
        fig.savefig(a.grafico, dpi=150)

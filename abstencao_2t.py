"""E se a abstenção cair só de um lado? Cenário de abstenção diferencial no 2º turno (não altera o modelo): modelos/abstencao-2t.json.

Hipótese (André Rocha, 19/10): nos estados em que só há eleição presidencial no 2º turno, e com o clima atual, muita gente não vai votar. Aqui:
  1) onde estão os 2º turnos de governador de 2026 (composição do eleitorado e dos votos de 2022);
  2) o efeito histórico de ter 2º turno de governador na variação da abstenção do 1º para o 2º turno (2018 e 2022, 54 UFs, regressão com efeito fixo de ano e voto bolsonarista);
  3) o que cada nível de abstenção extra muda no Lula/(Lula+Flávio): se os ausentes saem dos dois lados na proporção local, quase nada; se saem só do lado do Flávio, muda bastante.
Usa datasets/tse-presidente-uf.csv (aptos, comparecimento e votos por UF e turno). Os votos de 2022 são o peso dos estados.
  python abstencao_2t.py
ponytail: as listas de UFs com 2º turno de governador vêm de matérias (as fontes divergem em 2026: 5 a 7 UFs; usei a da Agência Brasil); a variação da abstenção tem n=54 e
intervalo que inclui zero; o cenário supõe que os ausentes eram eleitores do candidato na proporção do voto local e que o resto do país não muda."""
import json

import numpy as np
import pandas as pd

D = "datasets/"
# UFs com 2º turno de governador (matérias: 2018 e 2022 com 14 e 12 UFs; 2026 pela Agência Brasil, 7 UFs com o DF)
GOV2 = {2018: {"AM", "AP", "MG", "MS", "PA", "RS", "RO", "RN", "SE", "RR", "RJ", "SC", "SP", "DF"},
        2022: {"AL", "AM", "BA", "ES", "MS", "PB", "PE", "RS", "RO", "SC", "SP", "SE"},
        2026: {"AC", "AM", "DF", "ES", "RJ", "RN", "TO"}}
SEM_GOV2 = "sem 2º turno de governador"
COM_GOV2 = "com 2º turno de governador"


def _uf():
    d = pd.read_csv(D + "tse-presidente-uf.csv")
    d = d[~d.uf.isin(["VT", "ZZ"])].copy()
    d["abst"] = 1 - d.comparecimento / d.aptos
    return d


def historico(d):
    linhas, ano_tab = [], []
    for a in (2018, 2022):
        x = d[d.ano == a].pivot_table(index="uf", columns="turno", values=["abst", "pct_pt_dois", "aptos", "comparecimento"])
        x.columns = [f"{c}{t}" for c, t in x.columns]
        x["dabst"] = 100 * (x.abst2 - x.abst1)
        x["gov2"] = x.index.isin(GOV2[a])
        x["bols"] = 100 - x.pct_pt_dois2
        x["ano"] = a
        linhas.append(x.reset_index())
        g = x.groupby("gov2")
        ano_tab.append(dict(ano=a, abst1=round(100 * (1 - x.comparecimento1.sum() / x.aptos1.sum()), 2), abst2=round(100 * (1 - x.comparecimento2.sum() / x.aptos2.sum()), 2),
                            n_com=int(x.gov2.sum()), n_sem=int((~x.gov2).sum()), dabst_com=round(float(g.dabst.mean()[True]), 2), dabst_sem=round(float(g.dabst.mean()[False]), 2)))
    z = pd.concat(linhas)
    z["bols_c"] = z.bols - z.groupby("ano").bols.transform("mean")
    X = np.column_stack([np.ones(len(z)), z.gov2.astype(float), z.bols_c, (z.ano == 2022).astype(float)])
    y = z.dabst.to_numpy()
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    r = y - X @ b
    cov = (r @ r / (len(y) - 4)) * np.linalg.inv(X.T @ X)
    ic = lambda k: round(1.96 * float(np.sqrt(cov[k, k])), 2)
    return dict(n=int(len(z)), efeito_gov2=round(float(b[1]), 2), efeito_ic=ic(1), coef_bolsonarismo=round(float(b[2]), 3), coef_ic=ic(2), por_ano=ano_tab)


def base_2022():
    x = _uf()
    x = x[(x.ano == 2022) & (x.turno == 2)].set_index("uf").copy()
    x["gov26"] = x.index.isin(GOV2[2026])
    return x


def composicao(x):
    tot_pt, tot_bo = x.votos_pt.sum(), x.votos_antipt.sum()
    out = []
    for flag, nome in ((True, COM_GOV2), (False, SEM_GOV2)):
        g = x[x.gov26 == flag]
        out.append(dict(grupo=nome, ufs=int(len(g)), aptos_pct=round(100 * g.aptos.sum() / x.aptos.sum(), 1), lula_pct=round(100 * g.votos_pt.sum() / tot_pt, 1),
                        bolsonaro_pct=round(100 * g.votos_antipt.sum() / tot_bo, 1), bolsonaro_validos_pct=round(100 * g.votos_antipt.sum() / (g.votos_pt.sum() + g.votos_antipt.sum()), 1)))
    return out


def efeito(x, delta, lado="flavio"):
    """Mudança (p.p.) em Lula/(Lula+Flávio) se `delta` p.p. dos aptos das UFs sem 2º turno de governador deixam de votar: só do lado do Flávio ('flavio') ou dos dois lados
    na proporção do voto local ('proporcional'). Base: 2º turno de 2022."""
    pt, bo = x.votos_pt.astype(float), x.votos_antipt.astype(float)
    base = 100 * pt.sum() / (pt.sum() + bo.sum())
    m = ~x.gov26
    perda = delta / 100 * x.aptos[m]
    if lado == "flavio":
        bo = bo.copy()
        bo[m] = np.maximum(0, bo[m] - perda)
    else:
        f = 1 - perda / (pt[m] + bo[m])
        pt, bo = pt.copy(), bo.copy()
        pt[m], bo[m] = pt[m] * f, bo[m] * f
    return 100 * pt.sum() / (pt.sum() + bo.sum()) - base


def delta_para(x, alvo_pp):
    lo, hi = 0.0, 15.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if efeito(x, mid) < alvo_pp else (lo, mid)
    return (lo + hi) / 2


def main():
    d = _uf()
    x = base_2022()
    m = ~x.gov26
    aptos_sem, bo_sem = x.aptos[m].sum(), x.votos_antipt[m].sum()
    cen = []
    for delta in (0.5, 1, 2, 3, 4):
        cen.append(dict(delta=delta, eleitores_mi=round(delta / 100 * aptos_sem / 1e6, 2), pct_votos_flavio=round(100 * delta / 100 * aptos_sem / bo_sem, 1),
                        so_flavio=round(efeito(x, delta), 2), proporcional=round(efeito(x, delta, "proporcional"), 3)))
    s2 = 100 * json.load(open("modelos/parametros.json"))["turno2"]["p_pesquisas"]
    falta = 50 - s2
    quebra = []
    for nome, alvo in (("Para Lula ganhar 1 p.p.", 1.0), (f"Para Lula chegar a 50% (o modelo está em {s2:.1f}%)".replace(".", ","), falta)):
        dl = delta_para(x, alvo)
        quebra.append(dict(alvo=nome, ganho_pp=round(alvo, 2), delta=round(dl, 2), eleitores_mi=round(dl / 100 * aptos_sem / 1e6, 1), pct_votos_flavio=round(100 * dl / 100 * aptos_sem / bo_sem, 1)))
    out = dict(ufs_2026_com_gov2=sorted(GOV2[2026]), composicao=composicao(x), historico=historico(d), cenarios=cen, quebra=quebra, s2_modelo=round(s2, 2), base_2022=round(100 * x.votos_pt.sum() / (x.votos_pt.sum() + x.votos_antipt.sum()), 2),
               aptos_sem_mi=round(aptos_sem / 1e6, 1), votos_flavio_sem_mi=round(bo_sem / 1e6, 1))
    json.dump(out, open("modelos/abstencao-2t.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:1800])


if __name__ == "__main__":
    main()

"""Compara a projeção congelada do 1º turno com o resultado real (CSV com uf,lula,flavio,outros em % dos válidos).

Uso: python avaliar_projecao.py resultado-real.csv   (colunas: uf,lula,flavio,outros; pode incluir linha BR = nacional)
Mede, por cenário: erro nacional, MAE por UF (Lula, Flávio, margem), cobertura do IC 90% da margem e UFs com vencedor errado.
"""
import sys
import pandas as pd


def avaliar(real, proj):
    r = real.set_index("uf"); p = proj.set_index("uf").loc[lambda d: d.index.isin(r.index)]
    r = r.loc[p.index]; m = r.lula - r.flavio
    return dict(
        MAE_lula=(p.lula - r.lula).abs().mean(), MAE_flavio=(p.flavio - r.flavio).abs().mean(), MAE_margem=(p.margem - m).abs().mean(),
        cobertura_IC90=((m >= p.margem_p5) & (m <= p.margem_p95)).mean() * 100,
        vencedor_errado=int(((p.margem > 0) != (m > 0)).sum()), n_ufs=len(p))


if __name__ == "__main__":
    real = pd.read_csv(sys.argv[1])
    nac = real[real.uf == "BR"]
    real = real[real.uf != "BR"]
    for nome in ("pesquisas", "vies_se_repete"):
        res = avaliar(real, pd.read_csv(f"modelos/projecao-1turno-uf-{nome}.csv"))
        print(f"\n== cenário {nome} ==", {k: round(v, 1) for k, v in res.items()})
    if len(nac):
        import json
        j = json.load(open("modelos/projecao-1turno.json"))
        for nome in ("pesquisas", "vies_se_repete"):
            print(f"{nome}: Lula previsto {j[nome]['L'][1]} (real {nac.lula.iloc[0]}), Flávio {j[nome]['F'][1]} (real {nac.flavio.iloc[0]})")

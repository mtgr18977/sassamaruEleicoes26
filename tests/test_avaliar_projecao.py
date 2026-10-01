import pandas as pd
from avaliar_projecao import avaliar


def test_projecao_perfeita_tem_erro_zero_e_cobertura_total():
    proj = pd.DataFrame(dict(uf=["A", "B"], lula=[50., 30.], flavio=[40., 60.], margem=[10., -30.], margem_p5=[0., -40.], margem_p95=[20., -20.]))
    real = pd.DataFrame(dict(uf=["A", "B"], lula=[50., 30.], flavio=[40., 60.]))
    r = avaliar(real, proj)
    assert r["MAE_margem"] == 0 and r["cobertura_IC90"] == 100 and r["vencedor_errado"] == 0

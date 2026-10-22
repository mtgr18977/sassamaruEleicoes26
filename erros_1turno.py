"""Erro de cada instituto na última pesquisa antes do 1º turno de 2026, em Lula/(Lula+Flávio), contra o resultado do TSE (48,99%).

Fonte: datasets/pesquisas-1turno-final-2026.csv (as últimas pesquisas da semana da eleição, da Wikipedia e de matérias; o gráfico do Atlas de 4/10 serve de conferência).
Institutos sem os números da pesquisa (Veritá, DataTrends, IFP) entram só com o erro de margem do Atlas, convertido: erro em Lula/(L+F) ≈ erro de margem × 50 / (L+F do resultado).
Usado por sensibilidade_2t.py e vies_instituto.py. Positivo = a pesquisa deu a Lula mais do que ele teve."""
import pandas as pd

D = "datasets/"


def resultado():
    br = pd.read_csv(D + "resultado-2026-turno1.csv").query("uf == 'BR'").iloc[0]
    s = 100 * br.votos_lula / (br.votos_lula + br.votos_flavio)
    soma = 100 * (br.votos_lula + br.votos_flavio) / (br.votos_lula / br.lula * 100)   # Lula + Flávio, % dos válidos
    return float(s), float(soma)


def tabela():
    """DataFrame indexado por instituto: parcela (Lula/(L+F)), erro (p.p.), margem (erro de margem do Atlas), fonte ('pesquisa' ou 'atlas')."""
    real, soma = resultado()
    d = pd.read_csv(D + "pesquisas-1turno-final-2026.csv").set_index("instituto")
    tem = d.lula.notna() & d.flavio.notna()
    s = 100 * d.lula / (d.lula + d.flavio)
    d["parcela"] = s.where(tem)
    d["erro"] = (s - real).where(tem, d.erro_margem_atlas * 50 / soma).round(2)
    d["origem"] = ["pesquisa" if t else "atlas" for t in tem]
    return d


def erros():
    """Series instituto -> erro (p.p. em Lula/(Lula+Flávio))."""
    return tabela().erro

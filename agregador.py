"""Agregador de pesquisas: tendência suavizada (núcleo gaussiano) com viés de instituto e faixa de 90%.

Para cada série (ex.: Lula no 1º turno) e cada dia da grade:
  média(t) = Σ w_i · (y_i − h_inst(i)) / Σ w_i,   w_i = (n_i / DEFF) · exp(−(t − t_i)² / 2H²)
h_inst = desvio médio do instituto em relação à tendência, encolhido (K0 pesquisas "fantasma" em zero) e centrado em zero,
porque o nível absoluto não é identificável (mesma convenção de pesquisas.py). Faixa de 90% = erro amostral dos pesos
+ ruído residual entre pesquisas (TAU_PP, ASSUMIDO) + incerteza por falta de pesquisa recente (DERIVA_PP, ASSUMIDO).
Retorna também as versões "brutas" (sem ajuste de instituto) para o usuário comparar.
"""
import numpy as np
import pandas as pd

H_DIAS = 9.0        # largura do núcleo (desvio-padrão, dias): ~1 semana e meia de memória
DEFF = 1.5          # mesmo efeito de desenho de pesquisas.py
K0 = 2.0            # encolhimento do viés de instituto (equivale a 2 pesquisas em zero)
TAU_PP = 1.5        # ASSUMIDO: ruído residual entre pesquisas (p.p.) além do erro amostral
DERIVA_PP = 0.35    # ASSUMIDO: p.p. de incerteza por semana sem pesquisa perto do dia
Z90 = 1.645


def _kernel(dias_grade, dias_pesq, n):
    return (n / DEFF)[None, :] * np.exp(-0.5 * ((dias_grade[:, None] - dias_pesq[None, :]) / H_DIAS) ** 2)


def tendencia(d, grade, ajustar=True, iteracoes=6):
    """d: DataFrame com data, instituto, n, y (proporção 0-1). Retorna dict com m, lo, hi em % (listas, uma por dia da grade)."""
    d = d.dropna(subset=["y"]).sort_values("data")
    t0 = grade[0]
    dg = np.array([(g - t0).days for g in grade], float)
    dp = np.array([(x - t0).days for x in d.data], float)
    y, n, inst = d.y.to_numpy(float), d.n.to_numpy(float), d.instituto.to_numpy()
    nomes = sorted(set(inst))
    h = {i: 0.0 for i in nomes}
    W = _kernel(dg, dp, n)
    Wp = _kernel(dp, dp, n)

    def suave(yy, K):
        return (K * yy[None, :]).sum(1) / K.sum(1)

    if ajustar and len(nomes) > 1:
        for _ in range(iteracoes):
            ya = y - np.array([h[i] for i in inst])
            res = y - suave(ya, Wp)                                  # desvio de cada pesquisa vs. a tendência na sua data
            novo = {i: res[inst == i].sum() / ((inst == i).sum() + K0) for i in nomes}
            m = np.mean(list(novo.values()))
            h = {i: novo[i] - m for i in nomes}                      # centrado: o nível é a média dos institutos
    ya = y - np.array([h[i] for i in inst])
    m = suave(ya, W)
    wn = W / W.sum(1, keepdims=True)
    var_i = m[:, None] * (1 - m[:, None]) / (n / DEFF)[None, :] + (TAU_PP / 100) ** 2
    var = (wn ** 2 * var_i).sum(1)
    dist = np.min(np.abs(dg[:, None] - dp[None, :]), axis=1)
    var = var + (DERIVA_PP / 100) ** 2 * dist / 7
    se = np.sqrt(var)
    r = lambda a: [round(float(100 * x), 2) for x in a]
    return dict(m=r(m), lo=r(m - Z90 * se), hi=r(m + Z90 * se), vies={i: round(float(100 * v), 2) for i, v in h.items()})


def _serie(d, grade, k, nome, cor, col, extra=None):
    dd = d.assign(y=d[col])
    aj, br = tendencia(dd, grade, True), tendencia(dd, grade, False)
    pts = [dict(x=str(r.data.date()), y=round(100 * r.y, 2), inst=r.instituto, n=int(r.n), campo=str(r.campo_fim.date()))
           for r in dd.dropna(subset=["y"]).sort_values("data").itertuples()]
    m = aj["m"]
    ant = m[-15] if len(m) > 15 else m[0]
    return dict(k=k, nome=nome, cor=cor, aj=aj, bruta=br, pontos=pts, hoje=m[-1], delta14=round(m[-1] - ant, 2), vies=aj["vies"], **(extra or {}))


def _grade(d, hoje):
    return list(pd.date_range(d.data.min().normalize(), pd.Timestamp(hoje), freq="D"))


def _pacote(grade, turnos, hoje, nota):
    return dict(datas=[str(g.date()) for g in grade], hoje=str(pd.Timestamp(hoje).date()), turnos=turnos, nota=nota)


def presidente(hoje=None):
    """Lula × Flávio. 1º turno em % dos válidos (válidos = 100 − brancos/nulos/indecisos, ou a própria base 'validos');
    pesquisas sem essa informação ficam fora do 1º turno (ex.: AtlasIntel de 28/9, só Lula e Flávio). 2º turno: Lula/(Lula+Flávio)."""
    import pesquisas
    hoje = pesquisas.HOJE if hoje is None else hoje      # mesma data de referência do modelo
    d = pesquisas.preparar()
    d = d[d.data <= pd.Timestamp(hoje)].copy()
    val = np.where(d.base == "validos", 100.0, 100 - d.t1_bnin)
    d["v_lula"], d["v_flavio"] = d.t1_lula / val, d.t1_flavio / val
    d["l2"], d["f2"] = d.t2_lula / (d.t2_lula + d.t2_flavio), d.t2_flavio / (d.t2_lula + d.t2_flavio)
    g = _grade(d, hoje)
    t1 = [_serie(d, g, "lula", "Lula (PT)", "--pt", "v_lula"), _serie(d, g, "flavio", "Flávio Bolsonaro (PL)", "--anti", "v_flavio")]
    t2 = [_serie(d, g, "lula", "Lula (PT)", "--pt", "l2"), _serie(d, g, "flavio", "Flávio Bolsonaro (PL)", "--anti", "f2")]
    turnos = {"1": dict(titulo="1º turno", unidade="% dos votos válidos", ymin=20, ymax=60, ref=None, series=t1),
              "2": dict(titulo="2º turno", unidade="% dos votos válidos (Lula + Flávio = 100%)", ymin=40, ymax=60, ref=50, series=t2)}
    return _pacote(g, turnos, hoje, "Datafolha, Quaest, AtlasIntel, Real Time Big Data e Vox Brasil. Ponto = pesquisa (data = meio do campo).")


def rs(hoje=None):
    """Governador do RS. 1º turno: % dos válidos (candidatos; exclui brancos, nulos e indecisos). 2º turno: Zucco × Brizola
    (só pesquisas com o par), Zucco/(Zucco+Brizola)."""
    import rs_modelo as rm
    hoje = rm.HOJE if hoje is None else hoje
    d = rm.preparar()
    d = d[d.data <= pd.Timestamp(hoje)].copy()
    d["n"] = d.amostra
    d["zb_z"] = d.r2_zb_z / (d.r2_zb_z + d.r2_zb_b)
    d["zb_b"] = 1 - d.zb_z
    g = _grade(d, hoje)
    t1 = [_serie(d, g, "zucco", "Zucco (PL)", "--anti", "z"), _serie(d, g, "brizola", "Juliana Brizola (PDT)", "--pt", "b"),
          _serie(d, g, "souza", "Gabriel Souza (MDB)", "--s7", "s")]
    t2 = [_serie(d, g, "zucco", "Zucco (PL)", "--anti", "zb_z"), _serie(d, g, "brizola", "Juliana Brizola (PDT)", "--pt", "zb_b")]
    turnos = {"1": dict(titulo="1º turno", unidade="% dos votos válidos", ymin=10, ymax=55, ref=None, series=t1),
              "2": dict(titulo="2º turno Zucco × Brizola", unidade="% dos votos válidos (Zucco + Brizola = 100%)", ymin=35, ymax=65, ref=50, series=t2)}
    return _pacote(g, turnos, hoje, "Paraná Pesquisas, Quaest, Real Time Big Data, AtlasIntel e Neokemp. Ponto = pesquisa (data = fim do campo). Poucas pesquisas por instituto.")

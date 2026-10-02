import csv

from buscar_pesquisas import comparar, extrair, instituto, main, numero, periodo

# Página SINTÉTICA (valores inventados só para o teste), no formato típico de tabela da Wikipedia (rowspan/colspan, notas [1])
HTML = """
<table class="wikitable">
<tr><th rowspan="2">Instituto</th><th rowspan="2">Data</th><th rowspan="2">Amostra</th><th>Lula</th><th>Flávio Bolsonaro</th><th>Caiado</th><th>Zema</th><th>Renan Santos</th><th>Brancos/nulos</th></tr>
<tr><th>PT</th><th>PL</th><th>PSD</th><th>Novo</th><th>Missão</th><th></th></tr>
<tr><td>Quaest[1]</td><td>2 – 3 out 2026</td><td>2.004</td><td>41%</td><td>36%</td><td>3%</td><td>2%</td><td>4%</td><td>9%</td></tr>
<tr><td>AtlasIntel</td><td>23–28 set 2026</td><td>5.005</td><td>46,0</td><td>42,2</td><td>1,3</td><td>0,9</td><td>4,5</td><td>3</td></tr>
<tr><td>Instituto Desconhecido</td><td>1 out 2026</td><td>800</td><td>40</td><td>35</td><td>5</td><td>3</td><td>3</td><td>10</td></tr>
</table>
<table>
<tr><th>Instituto</th><th>Data</th><th>Lula</th><th>Flávio Bolsonaro</th><th>Brancos/nulos</th></tr>
<tr><td>Quaest</td><td>2 – 3 out 2026</td><td>45%</td><td>43%</td><td>12%</td></tr>
</table>
"""
OFICIAL = [dict(instituto="AtlasIntel", campo_ini="2026-09-23", campo_fim="2026-09-28", t1_lula="45.3", t1_flavio="42.2", t1_caiado="", t2_lula="47.6")]


def test_periodo_e_numero():
    assert periodo("27 set – 2 out 2026") == ("2026-09-27", "2026-10-02")
    assert periodo("22–23 set") == ("2026-09-22", "2026-09-23")
    assert periodo("26 a 30/9") == ("2026-09-26", "2026-09-30")
    assert periodo("1 out 2026") == ("2026-10-01", "2026-10-01")
    assert periodo("sem data") == (None, None)
    assert numero("45,3%") == 45.3 and numero("—") is None
    assert instituto("Real Time Big Data") == ("RealTimeBigData", True) and instituto("Xis")[1] is False


def test_extrair_junta_1o_e_2o_turno_pelo_instituto_e_data():
    q = next(r for r in extrair(HTML, "http://x") if r["instituto"] == "Quaest")
    assert (q["campo_ini"], q["campo_fim"], q["amostra"]) == ("2026-10-02", "2026-10-03", 2004)
    assert (q["t1_lula"], q["t1_flavio"], q["t1_renan"], q["t1_bnin"]) == (41, 36, 4, 9)
    assert (q["t2_lula"], q["t2_flavio"]) == (45, 43)           # tabela de 2º turno (sem Caiado/Zema)
    assert q["fonte_url"] == "http://x"


def test_comparar_marca_nova_e_divergente_e_ignora_instituto_fora_do_modelo():
    r = {c["instituto"]: c for c in comparar(extrair(HTML), OFICIAL)}
    assert r["Quaest"]["status"] == "nova"
    assert r["AtlasIntel"]["status"] == "divergente" and "t1_lula: 45.3 vs 46" in r["AtlasIntel"]["obs"]
    assert "Instituto Desconhecido" not in r
    assert "Instituto Desconhecido" in {c["instituto"] for c in comparar(extrair(HTML), OFICIAL, todos=True)}


def test_duplicada_identica_e_descartada():
    dup = [dict(OFICIAL[0])]
    cand = [dict(instituto="AtlasIntel", campo_ini="2026-09-23", campo_fim="2026-09-28", t1_lula=45.3, t1_flavio=42.2)]
    assert comparar(cand, dup) == []


def test_main_nao_altera_o_csv_oficial(tmp_path):
    pagina, saida = tmp_path / "p.html", tmp_path / "c.csv"
    pagina.write_text(HTML, encoding="utf-8")
    antes = open("datasets/pesquisas-2026.csv", "rb").read()
    assert main(["--html", str(pagina), "--saida", str(saida)]) == 0
    assert open("datasets/pesquisas-2026.csv", "rb").read() == antes
    linhas = list(csv.DictReader(open(saida, encoding="utf-8")))
    assert {l["status"] for l in linhas} <= {"nova", "divergente"} and all(l["fonte_url"] for l in linhas)


HTML2 = """
<h2>Primeiro turno</h2><h3>2026</h3><h4>Outubro</h4>
<table>
<tr><th>Contratante / Pesquisa</th><th>Data(s) de pesquisa</th><th>Tamanho da amostra</th><th>Lula PT</th><th>Flávio PL</th><th>Caiado PSD</th><th>Zema NOVO</th></tr>
<tr><td>Datafolha</td><td>3 Out</td><td>4 006</td><td>Resultado da pesquisa</td><td>Resultado da pesquisa</td><td>Resultado da pesquisa</td><td>Resultado da pesquisa</td></tr>
<tr><td>Quaest</td><td>1 Out – 2 Out</td><td>2 000</td><td>40%</td><td>35%</td><td>3%</td><td>2%</td></tr>
<tr><td>Quaest</td><td>1 Out – 2 Out</td><td>2 000</td><td>39%</td><td>30%</td><td>3%</td><td>2%</td></tr>
<tr><td>30 Set</td><td>30 Set</td><td>30 Set</td><td>Evento X</td><td>Evento X</td><td>Evento X</td><td>Evento X</td></tr>
<tr><td>Quaest</td><td>1 Out – 2 Out</td><td>999</td><td>40%</td></tr>
</table>
<h3>2025</h3>
<table>
<tr><th>Instituto</th><th>Data(s)</th><th>Lula</th><th>Flávio</th><th>Caiado</th></tr>
<tr><td>Quaest</td><td>10 Out</td><td>30%</td><td>20%</td><td>2%</td></tr>
</table>
<table>
<tr><th>Instituto</th><th>Data(s)</th><th>Lula</th><th>Flávio Bolsonaro</th><th>Tarcísio Rep</th><th>Caiado</th></tr>
<tr><td>Quaest</td><td>2 Out</td><td>40%</td><td>30%</td><td>10%</td><td>3%</td></tr>
</table>
"""


def test_regras_da_pagina_real_ano_agendada_separador_cenarios_e_outros_cenarios():
    r = extrair(HTML2, ate="2026-10-02")
    assert [(x["instituto"], x["campo_fim"]) for x in r] == [("Quaest", "2026-10-02")]   # ano 2025, agendada, separador, linha curta e tabela com Tarcísio ficam de fora
    assert r[0]["t1_lula"] == 40 and "cenarios" in r[0]["obs"]                          # primeira linha vence e avisa
    assert extrair(HTML2, ate="2026-10-01") == []                                         # data depois de `ate`: ignorada
    assert [x["campo_fim"] for x in extrair(HTML2, ano_padrao=2025)] == ["2025-10-10"]


def test_comparar_tolera_um_dia_e_ignora_diferenca_so_em_outros_e_brancos():
    o = [dict(instituto="Quaest", campo_ini="2026-10-01", campo_fim="2026-10-03", t1_lula="40", t1_flavio="35", t1_outros="0", t1_bnin="9")]
    c = dict(instituto="Quaest", campo_ini="2026-10-01", campo_fim="2026-10-02", t1_lula=40.0, t1_flavio=35.0, t1_outros=3.0, t1_bnin=20.0)
    assert comparar([c], o) == []


def test_amostra_diferente_entre_1o_e_2o_turno_fica_a_do_1o_e_avisa():
    h = ("<h3>2026</h3><table><tr><th>Instituto</th><th>Data(s)</th><th>Amostra</th><th>Lula</th><th>Flávio</th><th>Caiado</th></tr>"
         "<tr><td>Datafolha</td><td>28 Set – 1 Out</td><td>2 506</td><td>42%</td><td>38%</td><td>3%</td></tr></table>"
         "<table><tr><th>Instituto</th><th>Data(s)</th><th>Amostra</th><th>Lula</th><th>Flávio</th></tr>"
         "<tr><td>Datafolha</td><td>28 Set – 1 Out</td><td>2 002</td><td>48%</td><td>45%</td></tr></table>")
    r = extrair(h)[0]
    assert r["amostra"] == 2506 and (r["t1_lula"], r["t2_lula"]) == (42, 48) and "amostra difere" in r["obs"]

# Handoff — Sassamaru Eleições 2026

Data: 2/10/2026. Repo: `mtgr18977/sassamaruEleicoes26`. Responda em português, prefira tabelas e gráficos; o usuário escreve Python. Visão geral e método: `README.md`.

## Estado
| Item | Estado |
|---|---|
| ETL (`fetch_tse.py`) | rodado com dados reais do TSE; 12/12 OK contra o oficial; corrigidas dupla contagem (`_BR`+`_BRASIL`) e `cod_municipio` sem zero |
| Backtest (`backtest.py`, `nivel2.py`) | swing uniforme (δ real) erra ~6,2 p.p. por UF no 1º turno vs 9,95 da persistência; λ regional não melhora de forma clara |
| Pesquisas (`pesquisas.py`) | δ com house effect, recência, viés histórico (RMSE 3,6 p.p. 1º / 1,5 p.p. 2º; correção opcional por eleição: +2,3 / +0,8 p.p.), incerteza da tendência e piso assumido de 2,5 p.p. no 2º turno |
| Monte Carlo (`montecarlo.py`, JS) | UF e capitais; teste node compara JS com Python |
| Projeção 1º turno (`projecao.py`, JS) | Refeita em 2/10 com o Datafolha de 28/9–1/10: Lula 45,5 / Flávio 42,0 / demais 12,4; P(2º turno) 90%. A de 1/10 (45,2 / 42,1 / 12,6) está na tag `projecao-1turno-2026-10-01` |
| Aba RS (`rs.html`) | Governador: histórico TSE 2002–2022 por bloco/região, 10 pesquisas de 2026, chances e projeção por região (Zucco 90% · Brizola 10% com as pesquisas até 2/10 (sem pesquisa nova do RS desde 29/9); premissas assumidas, ver README) |
| Aba Bancada (`bancada.html`) | Deputado federal (31) e estadual (55): histórico TSE 2002–2022, bancada atual (API da Câmara; Wikipédia para a ALRS, não conferida), federações de 2026 e previsão por Monte Carlo. Backtest 2010–2022: 6,6 cadeiras trocadas; cobertura 82% da faixa de 80%. μ (migração), regra das sobras e federações são **assumidos** |
| Validação regional (`validar_regioes.py`) | `comparar()`: macro-regiões (Datafolha 22-23/9). `comparar_ufs()` (novo): SP/RJ/DF/MG/PE (Datafolha 28/9-1/10, divulgado 2/10, recorte por estado via Metropoles, **não conferido no TSE**) — modelo consistentemente ~2 a 5 p.p. abaixo da Datafolha em Lula/(Lula+Flávio) nos 5 estados e nos dois turnos; maior que a margem de erro em SP e DF no 1º turno. Não alimenta o δ nacional (já incorpora house effects de todos os institutos); é só checagem |
| Dashboard | `index.html` (Netlify serve a raiz), simulador interativo, mapa em tiles; `apps/eleicoes.html` |
| Testes | `python -m pytest -q tests`; `node tests/eleicoes-model.test.js`; `node tests/projecao-model.test.js`; `python atualizar.py` roda tudo |

## 1º turno realizado (4/10/2026) — atualização de 5/10
- Resultado (válidos, **preliminar, não conferido no TSE**): Flávio 47,03% (56.104.503) × Lula 45,16% (53.879.538); demais 7,81% (derivado). Wikipedia e O Tempo coincidem; o blog ao vivo da InfoMoney (47,50 × 44,61) foi descartado como parcial. Em `datasets/resultado-2026-turno1.csv` (BR + UFs com fonte; `obs` registra as dúvidas). O `votacao_candidato_munzona_2026.zip` do TSE estava só com cabeçalho em 5/10.
- Nova aba **Análise** (`analise.html`). O modelo errou o destino dos demais (projetado 12,4%, real 7,8%), não o Lula (45,5 × 45,16); as 4 últimas pesquisas deram a Lula 2,8–4,4 p.p. a mais na parcela Lula/(Lula+Flávio).
- Thread completa de Faganello (x.com/marcofaganello/status/2106989694500372912, 9 tweets) incorporada em `datasets/analise-faganello-2026.csv` (valor + id do tweet). Conferido contra o TSE 2022 do repositório: NE (Lula 21,75 mi; margem 12,97; déficit no resto 6,79) e base de aptos (−2,66 / +2,70 p.p.) batem. Abstenção: autor 20,8%, repositório 20,9% em 2022 — conferir. É associação entre municípios; próxima etapa dele é por seção. Não incluí o resultado de 2026 em `vies-pesquisas.csv` ainda (mudaria o viés/RMSE do modelo): decidir junto com a recalibração do 2º turno.
- Fontes divergem na contagem de estados (Wikipedia 14 + DF; Gazeta 15 + DF; TSE 2022 do repositório: 12 + DF). TO (Flávio 50,4%) é fonte única.
- Pendente: baixar o TSE oficial quando publicado, preencher todas as UFs, refazer o cruzamento por município (Censo/PIB), projeção do 2º turno com pesquisas pós-1º turno.

## RS e 2º turno (6/10/2026)
- Governador: Zucco (PL) eleito no 1º turno, 58,05% (3.516.048) × Brizola 31,65% × Souza 8,43% (O Tempo, 100% das seções; Agência Brasil trazia 57,88/31,88 a 91,53%, parcial). O modelo dava 43,0% a Zucco (faixa 37,6–48,6; 1,9% de chance de ganhar no 1º turno): erro de +15,0 p.p., 4,2× o erro sistemático assumido (3,6). Souza caiu de ~16,8 (modelo) para 8,4.
- Bancada (contagem minha a partir das listas CNN/Gazeta; **não conferida no TSE/ALRS**): federal PL 8, PT 5, PP 4, MDB 3…; estadual PL 12, PT 9, PP 7, MDB 5, PSD 5…. Modelo: 10 de 12 listas dentro da faixa de 80% (federal), 5,1 cadeiras trocadas (federal) e 10,4 (estadual) contra 6,6 no backtest. Teste pós-fato com o governador real quase não melhora (PL segue previsto em ~5): o desvio é do mecanismo (λ), não só da entrada — hipótese a investigar.
- Dados em `datasets/resultado-2026-rs-*.csv` (governador, bancada, cidades, mais votados), cada linha com a fonte. Cidades vêm de resumo automático de uma página do O Tempo (Pelotas com 47,1 nas duas colunas: conferir).
- Nova aba **2º turno** (`segundo-turno.html`, 1ª do menu): simulador de cenários (sem pesquisa pós-1º turno registrada). Pesquisas citadas em buscas como "de 3/10" (Datafolha, Quaest, Atlas, Gerp) são anteriores ao 1º turno e vieram de resumo de busca; **não** entraram.
- Mapas de calor por estado (`assets/mapa.js`, mesma grade do dashboard) na aba Análise (2022 completo; mudança do bloco de Flávio só onde há número com fonte, cinza no resto) e na aba 2º turno (2022 × cenário). Textos das abas Análise, Análise do governo, Análise da bancada e 2º turno estão em primeira pessoa (voz do autor do site); manter assim nas próximas edições dessas abas.
- Pendentes: TSE oficial; erro de 2026 em `vies-pesquisas.csv` e recalibração do SISTEMATICO_1T_PP do RS; mapa regional do RS e do Brasil em 2026; PR de viés (#17) ainda aberto.

## Senado (6/10/2026)
- Nova aba **Análise do Senado** (`analise-senado.html`), no molde da análise da bancada do RS. Dados **oficiais**: TSE `votacao_candidato_munzona_2026.zip` (gerado 5/10; o arquivo de 5/10 já tinha conteúdo, ao contrário do que o HANDOFF de 5/10 registrava; o `_BR` da presidencial continua só com cabeçalho) e API do Senado. `python fetch_tse_senado.py 2026|2018 <zip>` e `python fetch_tse_senado.py atual`.
- Resultado (TSE): 54 eleitos, PL 19, MDB 7, PT 6, PP/Novo/União/PSB 3 cada, PSDB/Podemos/Republicanos/PSD 2, PDT e Rede 1; Direita 32, Centro 11, Esquerda 11 (blocos de `rs_bancada.py`). Com as 27 de 2022: Direita 50 de 81 (3/5 = 49). 14 de 32 ocupantes que concorreram foram reeleitos. Cadeira mais apertada: RN (5.765 votos, Samanda de Lula × Zenaide Maia).
- Listas de imprensa divergiram (Agência Brasil somava 50 na tabela de composição; Piauí, Roraima, Tocantins e o partido de Van Hattem variavam entre fontes): usar só o TSE. Votos "anulados sub judice" (24 candidatos, nenhum eleito; AC: Gladson Camelí, 145 mil) ficam fora das margens (`votos_validos`).
- Seção 3 compara com duas réguas ingênuas (manter o ocupante; seguir a presidencial de 2022 na UF). **Seção 4: modelo do Senado** (`senado_modelo.py`; Senado 2014/2018/2022 do TSE em `datasets/tse-senado-*.csv`): logística por eleição da vaga ser da Direita contra o voto presidencial anti-PT da UF (x). β: −0,14 (2014), 0,72 (2018), 3,49 (2022), 2,60 (2026, com x = projeção do site) = Senado nacionalizado. Parâmetros da eleição anterior erram o **total** (2026: esperava 44,1 de 54, saíram 32; 2022: 9,4 de 27, saíram 19); com α calibrado ao total real a distribuição entre UFs erra 4,8 a 7,9 cadeiras trocadas, **sem vantagem clara** sobre a régua por ranking (2 de 3 eleições). Cuidado: o x de 2026 é a projeção do site (corr. 0,998 com 2022), não o voto real; o `_BR` presidencial do TSE ainda estava só com cabeçalho em 6/10 (zip de 5/10). Pendente: refazer com a presidencial real de 2026 por UF quando sair; incerteza do α (só 3 transições); blocos fixos (PSDB/MDB no Centro baixam a Direita de 2014). Reeleição casa nome do parlamentar com nome de urna (9 apelidos à mão em `senado.py`).

## Redesenho do site (6/10/2026, PR após a #20)
- **Menu:** `nav.ABAS` agora tem (arquivo, rótulo, grupo): Presidente (Presidente 2026, **2º turno depois**, Análise), Rio Grande do Sul (4 abas), Senado, Sobre. `nav.moldura(html, pagina)` aplica cabeçalho (marca + botão de tema), menu agrupado e rodapé; todo gerador chama isso (os templates continuam com `<nav class="tabs" ...>__NAV__</nav>`). O botão `#tema` é movido para o cabeçalho.
- **Notas laterais:** agora em todas as abas com seções (Análise, Análise do governo RS, Análise da bancada RS, Análise do Senado, 2º turno), no padrão do Presidente: `<section class="sec"><div>…</div><aside class="side" id="notaN">` + função `notas()` em cada template, com números calculados dos próprios dados (`nota2` do 2º turno é atualizada pelo simulador via `notaSim`). Manter a primeira pessoa nessas abas.
- **Visual/responsivo:** `assets/site.css` reescrito na base (serifa nos títulos, menu fixo só ≥1320 px, quebra em linhas até 901 px e rolagem horizontal fixa abaixo; tabelas `table.t` rolam no celular; grades com `minmax(0,1fr)` — antes Presidente e Bancada RS estouravam a largura em 375 px). `site.js` não quebra mais sem Chart.js (a Documentação dava erro e o botão de tema não funcionava).
- **Documentação** virou template (`apps/documentacao.template.html`, gerada por `python nav.py`) e foi reescrita: mapa do site, como ler, dados de 2026, 2º turno, Senado (ETL, blocos, réguas, modelo), análises, limites, como atualizar. Atualizar a data em "Atualizada em" quando mexer.
- Verificado em Chromium (1280 e 375 px): sem erro de JS e sem rolagem horizontal em nenhuma das 9 páginas.

## Decisões
- Bloco **Anti-PT** (Flávio em 2026); 2022 é a base por UF; município como base de dados, UF/capital como saída.
- Eleições sem Lula (2010, 2014 Dilma; 2018 Haddad) aparecem como contexto na página.
- Pesquisas: Datafolha, Quaest, AtlasIntel e Real Time Big Data.

## Dados do RS
Pesquisas do governador em `datasets/pesquisas-rs-governador-2026.csv` (cada linha com registro no TSE e fonte; somam 100%). Para atualizar: acrescentar a linha, rodar `python atualizar.py`. Cuidado com resumos de busca web: conferir a atribuição ao instituto na matéria.

## Regras de trabalho
- Não inventar dados: sem fonte, deixar vazio e anotar em `obs`.
- Projeção **não está mais congelada** (decisão de 2/10: ainda há pesquisas no sábado). A referência de 1/10 fica na tag `projecao-1turno-2026-10-01`; `python atualizar.py` refaz tudo. **Cada rodada: acrescentar as pesquisas ao CSV, atualizar `HOJE`/`HORIZONTE` em `pesquisas.py` e `HOJE` em `rs_modelo.py`.**
- Bancada: rodar `python fetch_tse_legislativo.py` (zips ou remotezip) e `python fetch_bancada_atual.py` (rede; a Wikipédia limita requisições) para atualizar `datasets/tse-legislativo-rs-*.csv` e `rs-bancada-atual.csv`; `python atualizar.py` refaz `bancada.html`.
- Pesquisas novas: `python buscar_pesquisas.py` gera candidatas em `datasets/candidatas.csv` (Wikipedia); conferir a fonte antes de passar a linha para `pesquisas-2026.csv`.
- Não apresentar baseline/backtest como "previsão" sem validação ponta a ponta.
- Só a Datafolha até 22–23/9 foi conferida; a de **28/9–1/10 entrou da Wikipedia (+ resumo de busca), sem relatório oficial nem registro no TSE** (amostra 2506 vs 2002 na própria fonte). Relatório oficial local em `docs/`, ignorado pelo git por direitos autorais). Quaest, Atlas, RTBD e as históricas não têm PDF: manter o aviso; há uma **nota técnica a escrever**.

## Próximos passos
1. Depois de 4/10: rodar `python fetch_tse.py` para 2026 (se o TSE publicar o arquivo) ou montar `resultado.csv` e `python avaliar_projecao.py resultado.csv`; reportar erro por UF e cobertura do IC.
2. Projeção do 2º turno (25/10) com o Monte Carlo existente, ajustando as pesquisas depois do 1º turno.
3. Completar pesquisas históricas (RTBD 2022, Quaest/Atlas 2018, 2006) e escrever a nota técnica.
4. Checar regras do TSE sobre divulgação de projeções antes de publicar.

## Lacunas conhecidas nas pesquisas 2026
Células vazias no CSV = "não localizei". Quaest sem 2º turno em setembro (exceto 24–27/9); Datafolha completa (conferida no relatório oficial); RTBD 26–30/9 em base de válidos e sem Renan Santos; Atlas 23–28/9 só Lula e Flávio.

## Atualização de 9/10/2026 (pesquisas de 2º turno pós-1º turno)
- Entraram Datafolha (6–8/10: Lula 45 × Flávio 49; BR-02949/2026) e AtlasIntel (3–8/10: 45,7 × 51,1; registro não localizado) em `pesquisas-2turno-pos-1t-2026.csv` e em `pesquisas-2026.csv`. Também as de véspera do 1º turno que faltavam: Datafolha 3/10 (47×46, BR-01708/2026), Quaest 2–3/10 (42×44, BR-02197/2026) e AtlasIntel 27/9–2/10 (47,6×47,4 totais; BR-00999/2026). Fontes: matérias (CNN, Brasil de Fato, Metrópoles, Exame); **relatórios oficiais não conferidos**.
- `HOJE` = 9/10, `HORIZONTE[2]` = 16. Novo `HOJE_1T` = 2/10: a projeção do 1º turno e o simulador do Presidente seguem congelados nessa data. `estimar()` agora ignora pesquisas posteriores a `hoje`.
- 2º turno: Lula/(Lula+Flávio) foi de 49,9% (90%: 45,8–54,0) para **48,1% (44,1–52,3)**; P(Lula>50%) 22,6%. O card "chance de ser eleito" ainda soma a chance de ganhar no 1º turno (8,6%), que já não existe: revisar para só o 2º turno.

- **Card do topo** (index): agora só o 2º turno (`chances2t` em `projecao-model.js`, fórmula fechada; sem correlação entre turnos). Lula 22,9% (faixa 14,1–22,9% entre os cenários de viés). Gráfico de evolução usa só s2/sd2 e vai até 9/10. O simulador e o 1º turno seguem congelados em `HOJE_1T`.

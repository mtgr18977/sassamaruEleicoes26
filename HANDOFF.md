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
| Dashboard | `index.html` (Netlify serve a raiz), simulador interativo, mapa em tiles; `apps/eleicoes.html` |
| Testes | `python -m pytest -q tests`; `node tests/eleicoes-model.test.js`; `node tests/projecao-model.test.js`; `python atualizar.py` roda tudo |

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

# Handoff — Sassamaru Eleições 2026

Data: 1/10/2026. Repo: `mtgr18977/sassamaruEleicoes26`. Responda em português, prefira tabelas e gráficos; o usuário escreve Python. Visão geral e método: `README.md`.

## Estado
| Item | Estado |
|---|---|
| ETL (`fetch_tse.py`) | rodado com dados reais do TSE; 12/12 OK contra o oficial; corrigidas dupla contagem (`_BR`+`_BRASIL`) e `cod_municipio` sem zero |
| Backtest (`backtest.py`, `nivel2.py`) | swing uniforme (δ real) erra ~6,2 p.p. por UF no 1º turno vs 9,95 da persistência; λ regional não melhora de forma clara |
| Pesquisas (`pesquisas.py`) | δ com house effect, recência, viés histórico (RMSE 3,6 p.p. 1º / 1,5 p.p. 2º) e incerteza da tendência |
| Monte Carlo (`montecarlo.py`, JS) | UF e capitais; teste node compara JS com Python |
| Projeção 1º turno (`projecao.py`, JS) | Lula 45,2 / Flávio 42,1 / demais 12,6; P(2º turno) 91%. **Congelada na tag `projecao-1turno-2026-10-01`** |
| Dashboard | `index.html` (Netlify serve a raiz), simulador interativo, mapa em tiles; `apps/eleicoes.html` |
| Testes | `python -m pytest -q tests`; `node tests/eleicoes-model.test.js`; `node tests/projecao-model.test.js`; `python atualizar.py` roda tudo |

## Decisões
- Bloco **Anti-PT** (Flávio em 2026); 2022 é a base por UF; município como base de dados, UF/capital como saída.
- Eleições sem Lula (2010, 2014 Dilma; 2018 Haddad) aparecem como contexto na página.
- Pesquisas: Datafolha, Quaest, AtlasIntel e Real Time Big Data.

## Regras de trabalho
- Não inventar dados: sem fonte, deixar vazio e anotar em `obs`.
- **Não sobrescrever `modelos/projecao-1turno*`** (a versão de 1/10 é a referência para avaliar depois de 4/10). `python atualizar.py` sem `--projecao` não toca neles.
- Não apresentar baseline/backtest como "previsão" sem validação ponta a ponta.
- Só a Datafolha foi conferida (relatório oficial local em `docs/`, ignorado pelo git por direitos autorais). Quaest, Atlas, RTBD e as históricas não têm PDF: manter o aviso; há uma **nota técnica a escrever**.

## Próximos passos
1. Depois de 4/10: rodar `python fetch_tse.py` para 2026 (se o TSE publicar o arquivo) ou montar `resultado.csv` e `python avaliar_projecao.py resultado.csv`; reportar erro por UF e cobertura do IC.
2. Projeção do 2º turno (25/10) com o Monte Carlo existente, ajustando as pesquisas depois do 1º turno.
3. Completar pesquisas históricas (RTBD 2022, Quaest/Atlas 2018, 2006) e escrever a nota técnica.
4. Checar regras do TSE sobre divulgação de projeções antes de publicar.

## Lacunas conhecidas nas pesquisas 2026
Células vazias no CSV = "não localizei". Quaest sem 2º turno em setembro (exceto 24–27/9); Datafolha completa (conferida no relatório oficial); RTBD 26–30/9 em base de válidos e sem Renan Santos; Atlas 23–28/9 só Lula e Flávio.

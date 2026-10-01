# Sassamaru Eleições 2026

Simulação estatística da eleição presidencial de 2026 a partir do histórico do TSE (2002–2022) e das pesquisas de 2026. Python faz ETL e ajuste; o JS roda a simulação no navegador. **É um modelo estatístico condicional às pesquisas, não uma pesquisa eleitoral nem uma previsão validada.**

- **Dashboard:** `index.html` ("Eleições Dashboard 2026": card com a chance de Lula e de Flávio serem eleitos, histórico do Lula, regiões, capitais, pesquisa × resultado, 2026 e simulador). `apps/eleicoes.html` é o simulador do Monte Carlo por UF/capital.
- **Projeção congelada do 1º turno (1/10/2026):** tag `projecao-1turno-2026-10-01`. Compare com o resultado real com `python avaliar_projecao.py resultado.csv`.

## Como rodar
```
pip install pandas pytest
python fetch_tse.py --offline          # CSVs de datasets/ a partir de datasets/tse_raw/*.zip (TSE)
python atualizar.py                    # pesquisas → Monte Carlo → página → testes (Python e node)
python atualizar.py --projecao         # também refaz a projeção do 1º turno (SOBRESCREVE a congelada)
```
Abra `index.html` direto no navegador (a página precisa de internet só para o Chart.js).

## Estrutura
| Arquivo | Papel |
|---|---|
| `fetch_tse.py` | ETL do TSE (município/zona → município, UF, capitais, nacional) e verificação contra o oficial |
| `backtest.py`, `nivel2.py` | Baselines (persistência, swing uniforme), backtest e λ regional (não melhora de forma clara o swing uniforme) |
| `pesquisas.py` | δ nacional a partir das pesquisas: house effect, recência, viés histórico → `modelos/parametros.json` |
| `montecarlo.py`, `modelos/eleicoes-model.js` | Monte Carlo por UF e capital (Python e JS, com teste de equivalência) |
| `projecao.py`, `modelos/projecao-model.js` | Projeção do 1º turno (Lula × Flávio × demais) com base em 2022 |
| `gerar_pagina_lula.py` | Gera `index.html` (dados embutidos) a partir de `apps/lula.template.html` |
| `validar_regioes.py` | Compara a distribuição regional do modelo com o cruzamento por região da Datafolha (22–23/9) |
| `datasets/` | CSVs do TSE e das pesquisas (`pesquisas-2026.csv`, `vies-pesquisas.csv`, `datafolha-regioes-2026-09-22.csv`) |

## Método em uma linha
Em logit, `y_UF,2026 = y_UF,2022 + δ`, com δ vindo das pesquisas; choque regional e ruído por UF **medidos** nos resíduos 2002–2022; um deslocamento comum é recalibrado para que o total nacional bata com o sorteado. No 1º turno há dois eixos: Lula/(Lula+Flávio) e o peso de Lula+Flávio.

## Limitações (leia antes de usar os números)
- **Sem validação ponta a ponta.** Só foi testada a parte "dado o total nacional, distribuir por UF" (backtest 2006–2022). O caminho pesquisa → resultado não tem backtest.
- **Pesquisas só parcialmente conferidas.** A série da Datafolha (22/7 a 23/9) foi conferida no relatório oficial (registro BR-00304/2026), que fica só local por direitos autorais. Quaest, Atlas, RTBD e as pesquisas históricas (2002, 2018, 2022) vêm de busca web (Wikipedia, Poder360, CNN, Gazeta do Povo, CartaCapital), sem os PDFs do TSE. Faltam RTBD 2022, Quaest/Atlas 2018 e pesquisas de 2006. Uma nota técnica sobre isso está prevista.
- **Viés histórico das pesquisas com poucas eleições.** Medido com a eleição como unidade (média das médias por eleição, para não contar 2022 três vezes): +2,3 p.p. no 1º turno (2002, 2018, 2022) e +0,8 p.p. no 2º (2018, 2022) a favor do PT, mas o erro-padrão da média é ~1,1 e ~0,7 p.p., então o viés mal se distingue de zero. A página mostra três cenários: **Pesquisas** (sem correção, padrão), **½ do viés histórico** e **Viés histórico** (extremo, não o mais provável). A projeção congelada de 1/10 usou a média por pesquisa (+3,0 p.p. no 1º turno).
- **Pouco histórico:** 5 transições eleitorais para estimar choques regionais; λ por região é instável. Falácia ecológica (resultado por UF não é comportamento individual).
- **Mudança de oferta eleitoral:** 2018 e as eleições de Dilma não têm Lula na urna; o "bloco anti-PT" muda de candidato a cada eleição.
- **Chance de ser eleito (card do topo):** soma vencer no 1º turno com vencer o 2º numa simulação conjunta; a correlação entre os erros dos dois turnos é assumida (0,5; a página mostra a faixa 0 a 1). Com o 2º turno em empate técnico, +1 p.p. de Lula/(Lula+Flávio) muda a chance de Lula em ~22 p.p.
- **Terceira via:** os "demais" entram como um bloco; o viés das pesquisas sobre eles não foi medido (2 p.p. assumidos).
- **Sem drift de opinião até a eleição** além da incerteza da tendência; a deriva semanal observada em 2026 não passa do ruído amostral.
- **Abstenção e comparecimento** ficam fixos em 2022. Regiões entram com choques independentes (o total nacional calibrado absorve o componente comum).
- **Regras do TSE/legislação** sobre divulgação de projeções devem ser checadas antes de qualquer publicação.

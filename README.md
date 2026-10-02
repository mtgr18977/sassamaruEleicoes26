# Sassamaru Eleições 2026

Simulação estatística da eleição presidencial de 2026 a partir do histórico do TSE (2002–2022) e das pesquisas de 2026. Python faz ETL e ajuste; o JS roda a simulação no navegador. **É um modelo estatístico condicional às pesquisas, não uma pesquisa eleitoral nem uma previsão validada.**

- **Abas:** `index.html` (Presidente 2026) e `rs.html` (Governo do RS 2026), com estilos e utilidades comuns em `assets/`.
- **Dashboard:** `index.html` ("Eleições Dashboard 2026": card com a chance de Lula e de Flávio serem eleitos, tema claro/escuro, notas laterais, histórico do Lula, regiões, capitais, pesquisa × resultado, 2026 e simulador). `apps/eleicoes.html` é o simulador do Monte Carlo por UF/capital.
- **Projeção do 1º turno:** refeita a cada rodada de pesquisas (`modelos/projecao-1turno*`). A versão de 1/10/2026 está na tag `projecao-1turno-2026-10-01`. Compare com o resultado real com `python avaliar_projecao.py resultado.csv`.

## Como rodar
```
pip install pandas pytest
python fetch_tse.py --offline          # CSVs de datasets/ a partir de datasets/tse_raw/*.zip (TSE)
python buscar_pesquisas.py             # (opcional, precisa de rede) candidatas de pesquisas novas em datasets/candidatas.csv
python atualizar.py                    # pesquisas → Monte Carlo → projeção do 1º turno → páginas → testes (Python e node)
```
Abra `index.html` direto no navegador (a página precisa de internet só para o Chart.js).

## Estrutura
| Arquivo | Papel |
|---|---|
| `fetch_tse.py` | ETL do TSE (município/zona → município, UF, capitais, nacional) e verificação contra o oficial |
| `backtest.py`, `nivel2.py` | Baselines (persistência, swing uniforme), backtest e λ regional (não melhora de forma clara o swing uniforme) |
| `buscar_pesquisas.py` | Busca pesquisas novas em tabelas HTML (Wikipedia) e grava **candidatas** em `datasets/candidatas.csv` (nova/divergente vs. o CSV oficial); não altera `pesquisas-2026.csv`. Conferir na fonte antes de promover a linha |
| `pesquisas.py` | δ nacional a partir das pesquisas: house effect, recência, viés histórico → `modelos/parametros.json` |
| `montecarlo.py`, `modelos/eleicoes-model.js` | Monte Carlo por UF e capital (Python e JS, com teste de equivalência) |
| `projecao.py`, `modelos/projecao-model.js` | Projeção do 1º turno (Lula × Flávio × demais) com base em 2022 |
| `gerar_pagina_lula.py` | Gera `index.html` (dados embutidos) a partir de `apps/lula.template.html` |
| `validar_regioes.py` | Compara a distribuição regional do modelo com o cruzamento por região da Datafolha (22–23/9) |
| `fetch_tse_rs.py`, `regioes_rs.py`, `rs_dados.py` | ETL do governador do RS (zips do TSE já baixados), mapa município → mesorregião do IBGE (rede) e blocos/unidades |
| `rs_modelo.py`, `modelos/rs-model.js` | Aba do RS: estimativa das pesquisas, chances (1º e 2º turno simulados juntos) e projeção por região, em Python e JS (teste de equivalência) |
| `gerar_pagina_rs.py` | Gera `rs.html` a partir de `apps/rs.template.html` |
| `datasets/` | CSVs do TSE e das pesquisas (`pesquisas-2026.csv`, `vies-pesquisas.csv`, `datafolha-regioes-2026-09-22.csv`, `pesquisas-rs-governador-2026.csv`, `tse-governador-rs-municipio.csv`, `rs-municipios-regioes.csv`) |

## Método em uma linha
Em logit, `y_UF,2026 = y_UF,2022 + δ`, com δ vindo das pesquisas; choque regional e ruído por UF **medidos** nos resíduos 2002–2022; um deslocamento comum é recalibrado para que o total nacional bata com o sorteado. No 1º turno há dois eixos: Lula/(Lula+Flávio) e o peso de Lula+Flávio.

## Limitações (leia antes de usar os números)
- **Sem validação ponta a ponta.** Só foi testada a parte "dado o total nacional, distribuir por UF" (backtest 2006–2022). O caminho pesquisa → resultado não tem backtest.
- **Pesquisas só parcialmente conferidas.** A série da Datafolha (22/7 a 23/9) foi conferida no relatório oficial (registro BR-00304/2026), que fica só local por direitos autorais. Quaest, Atlas, RTBD e as pesquisas históricas (2002, 2018, 2022) vêm de busca web (Wikipedia, Poder360, CNN, Gazeta do Povo, CartaCapital), sem os PDFs do TSE. Faltam RTBD 2022, Quaest/Atlas 2018 e pesquisas de 2006. Uma nota técnica sobre isso está prevista.
- **Viés histórico das pesquisas com poucas eleições.** Medido com a eleição como unidade (média das médias por eleição, para não contar 2022 três vezes): +2,3 p.p. no 1º turno (2002, 2018, 2022) e +0,8 p.p. no 2º (2018, 2022) a favor do PT, mas o erro-padrão da média é ~1,1 e ~0,7 p.p., então o viés mal se distingue de zero. A página mostra três cenários: **Pesquisas** (sem correção, padrão), **½ do viés histórico** e **Viés histórico** (extremo, não o mais provável). A projeção congelada de 1/10 usou a média por pesquisa (+3,0 p.p. no 1º turno).
- **Pouco histórico:** 5 transições eleitorais para estimar choques regionais; λ por região é instável. Falácia ecológica (resultado por UF não é comportamento individual).
- **Mudança de oferta eleitoral:** 2018 e as eleições de Dilma não têm Lula na urna; o "bloco anti-PT" muda de candidato a cada eleição.
- **Chance de ser eleito (card do topo):** soma vencer no 1º turno com vencer o 2º numa simulação conjunta; a correlação entre os erros dos dois turnos é assumida (0,5; a página mostra a faixa 0 a 1). Com o 2º turno em empate técnico, +1 p.p. de Lula/(Lula+Flávio) muda a chance de Lula em ~15 p.p. (a página calcula o valor atual).
- **Terceira via:** os "demais" entram como um bloco; o viés das pesquisas sobre eles não foi medido (2 p.p. assumidos).
- **Piso de incerteza no 2º turno (assumido):** 2,5 p.p. em Lula/(Lula+Flávio) (`SD_PISO_2T_PP` em `pesquisas.py`). O erro medido (1,5 p.p.) é de pesquisas finais; a 24 dias da eleição tende a ser maior. É um parâmetro, não uma medida.
- **Sem drift de opinião até a eleição** além da incerteza da tendência; a deriva semanal observada em 2026 não passa do ruído amostral.
- **Abstenção e comparecimento** ficam fixos em 2022. Regiões entram com choques independentes (o total nacional calibrado absorve o componente comum).
- **Regras do TSE/legislação** sobre divulgação de projeções devem ser checadas antes de qualquer publicação.

## Limitações da aba do RS (governador)
- **Pesquisas extraídas de matérias** (Gazeta do Povo, CartaCapital, Band, Terra Brasil, Studio TV), sem conferência no TSE. Uma busca web chegou a atribuir ao Datafolha uma pesquisa que era do Real Time Big Data; por isso cada linha do CSV traz o registro no TSE e a fonte. Há 10 pesquisas de 5 institutos, poucas por instituto, com house effects grandes.
- **Sem histórico de pesquisas estaduais.** O erro sistemático do 1º turno (3,6 p.p.) usa como proxy o RMSE nacional medido; o piso do 2º turno (2,5 p.p.) é o mesmo assumido no nacional. Não dá para medir o viés das pesquisas do RS.
- **Blocos por partido** (esquerda: PT, PDT, PSOL, PSB, PV e nanicos; centro: MDB/PMDB, PSDB, PPS; direita: PL, PP, PSC, Novo e demais) são um pressuposto. Zucco = direita, Brizola = esquerda, Souza e Maranata = centro. A direita quase não existia em 2010 (0,3%), o que torna instáveis razões em log que a envolvem.
- **Ruído regional de 5 transições** (2002–2022), com 8 unidades (mesorregiões, a Grande POA sem a capital e Porto Alegre à parte); sem correlação espacial.
- **Sem Eduardo Leite** (limitado por mandato) o centro encolhe de 26,8% (2022) para ~17% nas pesquisas: a base 2022 do centro não se aplica diretamente.

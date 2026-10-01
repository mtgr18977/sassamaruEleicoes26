# Handoff — Sassamaru Eleições 2026 (sessão cloud → Claude Code local)

Data: 1/10/2026. Repo: `mtgr18977/sassamaruEleicoes26`. Responda em português, prefira tabelas e gráficos; usuário escreve Python.

## 1. Objetivo

Módulo de previsão da eleição presidencial 2026 na filosofia do Sassamaru: dados históricos → modelo simples e regularizado → Monte Carlo → backtest como porta de regressão. Python faz ETL e ajuste (`pandas`, `statsmodels`/PyMC) e exporta `parametros.json`. O JS (`modelos/eleicoes-model.js`, `apps/eleicoes.html`) só roda o Monte Carlo no navegador. Detalhes completos em `docs/sassamaru-eleicoes-plano.md`; pesquisas em `docs/sassamaru-eleicoes-pesquisas.md`.

**Datas:** 1º turno 4/10/2026; 2º turno 25/10/2026. A previsão do 1º turno precisa ser congelada e commitada **antes de 4/10**. O modelo completo mira o 2º turno.

## 2. Decisões fechadas

| Tema | Decisão |
|---|---|
| Alvo | 1º e 2º turno |
| Bloco | **Anti-PT**: PT (Lula/Dilma/Haddad) vs. adversário do PT no 2º turno (Serra 2002/2010, Alckmin 2006, Aécio 2014, Bolsonaro 2018/2022); resto = "outros" |
| Granularidade | Município como base; agrega para UF e capital (27 capitais; Brasília é DF e capital; exterior = "ZZ") |
| Histórico | 2002, 2006, 2010, 2014, 2018, 2022 |
| Pesquisas | Só Datafolha, Quaest, AtlasIntel, Real Time Big Data |
| Cenário 2026 | Lula (PT) vs. Flávio Bolsonaro (PL); terceira via: Cury, Caiado, Renan Santos, Zema |

## 3. Modelo (em logit do % PT nos válidos, `y = logit(p)`)

| Nível | Fórmula | Uso |
|---|---|---|
| 0 | `p(2026) = p(2022)` | baseline obrigatório |
| 1 | `y_i = y_i,2022 + δ` | MVP |
| 2 | `y_i = y_i,2022 + λ_i·δ` | versão recomendada |
| 3 | hierárquico bayesiano, partial pooling | se sobrar tempo |
| 4 | + covariáveis | cuidado com overfitting |

- **δ** vem das pesquisas: média ponderada com decaimento por recência, peso por amostra e correção de house effect. Incerteza = erro amostral + viés histórico das pesquisas (2022 superestimou Lula no 1º turno) + variância entre institutos.
- **λ_i** é estimado em 2002–2022 por região/UF, com priors fortes (5 transições por unidade).
- **Monte Carlo:** sorteia δ, choque regional correlacionado (N, NE, CO, SE, S) e ruído por município; soma votos (voto popular direto). Saídas: P(vitória), P(2º turno), margem, tabela por UF/capital com intervalo.
- **Capitais:** testar `capital = estado + gap`; só usar se o gap for estável.
- **Backtest:** leave-one-election-out (prever 2010, 2014, 2018, 2022) contra persistência e swing uniforme. Métricas: MAE em p.p. por UF e capital, erro nacional, acerto do vencedor por UF, calibração. Medir separadamente o erro do δ (usar δ real) e o da distribuição entre UFs. **Se não bater a persistência, não publicar como "previsão".**

## 4. Estado do repositório (branch principal, após o PR #1)

| Caminho | O que é | Estado |
|---|---|---|
| `fetch_tse.py` | Baixa/lê votação presidente do TSE por município/zona, classifica blocos, gera CSVs, verifica contra o oficial | **nunca rodou contra o TSE real** |
| `tests/test_fetch_tse.py` | 9 testes unitários (zips sintéticos) | 9/9 passando (`python -m pytest -q tests`) |
| `datasets/pesquisas-2026.csv` | 25 rodadas dos 4 institutos | pronto, com lacunas (seção 6) |
| `docs/` | plano, resumo das pesquisas, gráfico de tendência | prontos |
| `.gitignore` | ignora `datasets/tse_raw/` | ok |

Não existem ainda: `modelos/`, `apps/`, `package.json`/`npm test`, README do módulo, código das Fases 1+. Não há código de futebol neste repo, então não há Brasileirão a proteger aqui (se você trouxer o Sassamaru para este repo, mudanças que o afetem passam por `npm run test:backtest`, e `modelos/model.js` e `modelos/selecoes-model.js` não devem ser tocados).

## 5. Próximos passos (ordem)

**Fase 0: rodar o `fetch_tse.py` com os dados reais** (o usuário já baixou os dados do TSE)

1. Colocar os zips em `datasets/tse_raw/` com estes nomes exatos (o script só reconhece estes):
   - `votacao_candidato_munzona_AAAA.zip` (obrigatório)
   - `detalhe_votacao_munzona_AAAA.zip` (opcional: aptos, comparecimento, brancos, nulos; sem ele use `--sem-detalhe`)
   Se os arquivos baixados tiverem outro nome, renomear ou ajustar.
2. `pip install pandas pytest`, depois `python fetch_tse.py --inspecionar 2022 --offline`. Conferir arquivos no zip, colunas e o mapeamento. Repetir para 2002 e 2010 (layouts antigos).
3. `python fetch_tse.py --offline`. A tabela de verificação deve sair toda `OK` (tolerância 0,15 p.p.).
4. Se algum ano divergir, **investigar a causa antes de seguir** (aliases de coluna, dupla contagem por presidente repetido no arquivo nacional e nos de UF, bloco errado, encoding). Atualizar os testes se o comportamento mudar.

**Riscos conhecidos do script:**
1. O padrão de URL do CDN e os zips de 2002–2010 não foram confirmados; com `--offline` a URL não importa.
2. Nomes de coluna mudam entre anos; aliases em `ALIASES_CANDIDATO`/`ALIASES_DETALHE`; se falhar, o script mostra as colunas reais.
3. Os valores oficiais em `OFICIAL_PT` foram escritos de memória e **precisam ser conferidos no site do TSE**. Se a divergência for só nessa tabela, corrigir a tabela com a fonte, nunca ajustar a tolerância ou o parsing para "passar".
4. Prefere o arquivo `_BRASIL`/`_BR`; avisa sobre duplicatas.
5. `cod_municipio` é código do **TSE**, não do IBGE.

**Depois da Fase 0:**

5. Conferir saídas: 27 capitais por (ano, turno); totais nacionais; municípios criados/extintos entre 2002 e 2022 (listar e propor tratamento, ex.: agregar ao município-mãe ou excluir da estimativa de λ).
6. **Fase 1:** baselines (persistência e swing uniforme) em Python + backtest leave-one-election-out, com tabela de erro por UF e por capital.
7. Só então o nível 2 (λ regional) e a camada de pesquisas (δ com incerteza).
8. README do módulo com limitações: poucos dados, falácia ecológica, mudança de oferta eleitoral, terceira via no 1º turno, viés das pesquisas, abstenção. Deixar claro que é **modelo estatístico, não pesquisa eleitoral**, e checar as regras do TSE/legislação sobre divulgação de projeções antes de publicar.

## 6. Pesquisas: lacunas conhecidas

Células vazias no CSV significam "não localizei", não zero. `base` = `total` ou `validos`. Compare institutos sempre em Lula/(Lula+Flávio) ou votos válidos (Atlas deixa ~1–2% de indecisos; os outros 7–15%).

| Item | Problema |
|---|---|
| Datafolha e Quaest, 2º turno de setembro | não localizado |
| Quaest 28/set | sem datas de campo e amostra |
| Datafolha 22–23/set | campo diverge (22–24 na Wikipedia); divulgação 24 ou 28/set |
| Datafolha 1–3/set | Wikipedia diz 1–2/set; cenário com e sem Marçal (usado: sem) |
| RTBD 19–23/set | 2º turno diverge (Lula 44 ou 45) |
| RTBD 26–30/set | base em válidos; sem Renan Santos |
| Atlas 23–28/set | só Lula e Flávio |

Antes de usar no modelo, conferir contra os PDFs registrados no TSE (BR-xxxxx/2026).

Última rodada, Lula/(Lula+Flávio) no 1º turno: Datafolha 52,6%, Quaest 53,4%, Atlas 51,8%, RTBD 52,9%. Gap Lula−Flávio caiu em todos desde agosto (Atlas 9,7→3,1 p.p.; RTBD 8,0→5,0; Quaest 7,0→5,0; Datafolha 6,0→4,0).

## 7. Regras de trabalho

- Não inventar dados: se não achar, deixar vazio e anotar em `obs`.
- Rodar os testes a cada mudança; commits pequenos e claros.
- Não apresentar baseline ou backtest como "previsão" sem passar na regra do item 3.
- Mostrar tabelas e gráficos quando ajudar.

## 8. Decisões ainda em aberto

| Pergunta | Observação |
|---|---|
| Prazo do 1º turno | Sem os CSVs validados, a Fase 1 pode não sair antes de 4/10; o alvo realista é o 2º turno. Se der tempo, congelar a persistência/swing uniforme como teste honesto. |
| Onde ficam os zips | `datasets/tse_raw/` está no `.gitignore`; os CSVs gerados em `datasets/tse-presidente-*.csv` podem ser commitados. |

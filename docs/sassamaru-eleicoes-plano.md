# Sassamaru Eleições 2026 — plano de design

Ideia: reaproveitar a filosofia do Sassamaru (dados históricos → modelo estatístico → Monte Carlo → backtest como porta de regressão) para prever a eleição presidencial, usando a tendência PT vs. bloco anti-PT/Bolsonaro em estados e capitais.

---

## 1. Aviso de calendário (leia primeiro)

| Evento | Data |
|---|---|
| 1º turno | domingo, 4 de outubro de 2026 |
| 2º turno (se houver) | domingo, 25 de outubro de 2026 |

O 1º turno é daqui a poucos dias. Realisticamente:

- **Dá para fazer** um MVP simples (swing uniforme + dados do TSE) antes do 4/10 e **congelar a previsão com timestamp no git**. Isso vira um teste honesto: previsão publicada antes do resultado.
- **Mira de verdade:** o modelo mais completo é para o **2º turno (25/10)**, que é binário e muito mais limpo de modelar.
- Modelo com 2–3 eleições de histórico **não substitui pesquisa**. Trate como complemento (ver seção 4).

---

## 2. O que muda em relação ao futebol

| Aspecto | Brasileirão (Sassamaru) | Eleição presidencial |
|---|---|---|
| Amostra | ~380 jogos/temporada × várias temporadas | 1 "jogo" a cada 4 anos por unidade |
| Observações por unidade | centenas | 3 (ou 5 se voltar a 2002) |
| Saída | placar (contagem) → Poisson | **proporção** (soma 100%) → logit / Dirichlet |
| Fonte de "tendência" | histórico de gols | histórico de voto **+ pesquisas atuais** |
| Backtest | walk-forward em ~955 jogos | leave-one-election-out, só ~2–4 transições |
| Risco principal | ruído | **overfitting** e pouquíssimos dados |

Consequência: o modelo precisa ser **muito mais simples e muito mais regularizado** que o do Brasileirão. Poucos parâmetros, priors fortes.

---

## 3. Dados

### 3.1 Fonte

- **TSE Dados Abertos** (`dadosabertos.tse.jus.br`): "Resultados" por eleição. O arquivo útil é o de **votação por candidato, município e zona** (`votacao_candidato_munzona_AAAA`), mais o de **detalhe da votação** (aptos, comparecimento, brancos, nulos). Confira os nomes exatos das colunas ao baixar, porque mudam um pouco entre anos.
- Alternativa: **Base dos Dados** (`basedosdados.org`), que já tem as tabelas do TSE tratadas, acessíveis via BigQuery ou pacote Python.

### 3.2 Recomendação: baixe no nível de **município**, não de estado

Você falou em estados e capitais. Minha sugestão é coletar por **município** (ou zona) e agregar:

| Unidade | Qtd | Vantagem |
|---|---|---|
| Estado (UF) | 27 | resultado final que todo mundo quer ver |
| Capital | 27 | sai de graça, é só filtrar o município |
| Município | ~5.570 | muito mais dados pra estimar sensibilidade, e dá pra agregar para qualquer recorte |

Com 27 UFs × 3 eleições você tem 81 pontos. Com municípios, milhares. Estimar a sensibilidade de cada região ao swing nacional fica bem mais robusto.

Atenção: Brasília é Distrito Federal **e** capital ao mesmo tempo; trate como caso especial. Voto no exterior vem como "ZZ" e deve ficar como unidade separada.

### 3.3 Esquema de CSV sugerido (análogo ao `campeonato-brasileiro-limpo.csv`)

```
ano, turno, uf, cod_municipio, municipio, eh_capital,
aptos, comparecimento, brancos, nulos, validos,
votos_bloco_pt, votos_bloco_direita, votos_outros
```

### 3.4 Mapeamento de candidato → bloco

Aqui está a parte que exige decisão sua, porque "tendência" depende de como você classifica:

| Eleição | Bloco PT | Bloco anti-PT / direita | Outros relevantes (1º turno) |
|---|---|---|---|
| 2014 | Dilma (PT) | Aécio (PSDB) | Marina Silva (~21%) |
| 2018 | Haddad (PT) | Bolsonaro (PSL) | Ciro (~12%) |
| 2022 | Lula (PT) | Bolsonaro (PL) | Tebet (~4%), Ciro (~3%) |
| 2026 | Lula (PT) | Flávio Bolsonaro (PL) | Caiado, Zema, Renan Santos e outros |

Cuidados:

- **2014 não é bolsonarismo.** Aécio é anti-PT, mas não é "voto Bolsonaro". Se o seu bloco for "bolsonarista", 2014 não entra; se for "anti-PT", entra. Sugiro usar **bloco anti-PT** como variável principal e, como análise extra, testar só 2018 e 2022.
- **Flávio ≠ Jair.** A suposição de que o voto do pai transfere integralmente para o filho é um **parâmetro de incerteza**, não um fato.
- O 1º turno tem muita massa fora dos dois blocos (Marina 2014, Ciro 2018). Por isso o 2º turno é bem mais confiável como alvo.

### 3.5 Resultados nacionais de referência (2º turno)

| Ano | PT | Adversário | Margem |
|---|---|---|---|
| 2002 | Lula 61,3% | Serra 38,7% | +22,6 |
| 2006 | Lula 60,8% | Alckmin 39,2% | +21,7 |
| 2010 | Dilma 56,1% | Serra 43,9% | +12,1 |
| 2014 | Dilma 51,6% | Aécio 48,4% | +3,3 |
| 2018 | Haddad 44,9% | Bolsonaro 55,1% | −10,3 |
| 2022 | Lula 50,9% | Bolsonaro 49,1% | +1,8 |

(Percentuais sobre votos válidos, arredondados. Confirme no TSE ao montar o CSV.)

**Sugestão importante:** vá além de 3 eleições. Com 2002, 2006 e 2010 a série "voto PT em cada UF" ganha **5 transições** em vez de 2, o que muda bastante a qualidade da estimativa. O tratamento muda (anti-PT = tucano nesses anos), mas a variável "% PT no 2º turno" é contínua.

---

## 4. Modelo proposto (do simples ao completo)

### Insight central

Só com histórico você não sabe **em que direção o país está se movendo em 2026**. O histórico diz *como cada estado reage* a uma mudança nacional; quem diz *quanto o país mudou* são as **pesquisas**. Então o modelo tem duas camadas:

1. **Nacional:** quanto o PT sobe/desce em relação a 2022 (vem de pesquisas + prior histórico).
2. **Estadual/municipal:** como essa mudança nacional se distribui (vem do histórico).

É a mesma lógica dos modelos de forecast eleitoral conhecidos: fundamentos/pesquisa no nível nacional, estrutura histórica no nível local.

### Níveis de complexidade

| Nível | Nome | Fórmula (em logit do % PT nos válidos) | Parâmetros | Quando usar |
|---|---|---|---|---|
| 0 | Persistência | `p(2026) = p(2022)` | 0 | **baseline obrigatório** |
| 1 | Swing uniforme | `y_i,2026 = y_i,2022 + δ` | 1 (δ) | MVP antes do 4/10 |
| 2 | Swing com sensibilidade | `y_i,2026 = y_i,2022 + λ_i · δ` | δ + λ por região | versão recomendada |
| 3 | Hierárquico bayesiano | `y_i,t = a_i + λ_i·δ_t + ε`, com partial pooling | dezenas | se sobrar tempo |
| 4 | + covariáveis | renda, escolaridade, % evangélicos, cobertura de programas sociais | muitos | **cuidado com overfitting** |

Onde `y = logit(%PT nos votos válidos)`, `δ` = swing nacional em logit, `λ_i` = quanto a unidade `i` se mexe em relação ao país (λ > 1 = mais volátil, λ < 1 = mais "teimosa").

### Por que logit e não pontos percentuais

Em estados com 80% de PT (parte do Nordeste), um swing de +5 p.p. é impossível; em logit, o efeito encolhe naturalmente perto dos extremos e os valores previstos nunca saem de [0, 1].

### Estimando δ (swing nacional)

```
δ_2026 ~ Normal(μ, σ²)
μ  = média ponderada das pesquisas de 2º turno (convertida para logit, com a média nacional de 2022 como âncora)
σ² = erro histórico das pesquisas  +  erro sistemático do modelo estrutural
```

Pontos de atenção:

- Em 2022, as pesquisas **subestimaram o Bolsonaro** no 1º turno. Um viés assim deve ser estimado e embutido na variância, não ignorado.
- Pesquisas devem ser ponderadas por instituto, tamanho de amostra e recência (decaimento exponencial, análogo ao peso temporal do Sassamaru).

### Simulação Monte Carlo

Para cada uma de N simulações (ex.: 10.000):

1. Sorteia `δ`.
2. Sorteia choque regional `r_g` (Norte, Nordeste, Centro-Oeste, Sudeste, Sul), porque erros são **correlacionados** entre estados vizinhos.
3. Sorteia ruído idiossincrático `ε_i` por unidade.
4. Calcula `%PT_i`, pondera pelos votos válidos projetados (comparecimento de 2022 como base, com ajuste), e **soma votos**, já que a eleição presidencial é voto popular direto, sem colégio eleitoral.
5. Registra: vencedor nacional, margem, vencedor por UF, e (no 1º turno) se alguém passa de 50% dos válidos.

Saídas, em tabela e gráfico (você curte): probabilidade de vitória, distribuição da margem, mapa/tabela por UF com intervalo, "estados-chave" (maior incerteza × maior peso em votos).

### Capitais

Duas opções:

| Abordagem | Como | Prós/contras |
|---|---|---|
| A. Modelar capital como unidade | mesma fórmula, λ próprio | simples, mas poucos dados por capital |
| B. Gap capital vs. estado | `gap = logit(capital) − logit(estado sem a capital)`; prevê `capital = estado + gap` | usa o fato de que capitais costumam divergir do interior de forma persistente |

Teste antes se o gap é **estável** entre 2014, 2018 e 2022. Se oscilar muito, não vale usar.

---

## 5. Backtest (a "porta de regressão" do projeto)

No Sassamaru, o baseline constante 47/27/26 é a régua. Aqui:

| Comparação | O que mede |
|---|---|
| Persistência (repete a última eleição) | se o modelo agrega algo |
| Swing uniforme | se sensibilidade λ_i ajuda |
| Modelo completo | o resultado final |

**Protocolo:** leave-one-election-out.
Treina com eleições anteriores a T, prevê T, mede o erro. Com 2002–2022 dá para prever 2010, 2014, 2018 e 2022.

**Métricas:**

- MAE em p.p. por UF (e por capital)
- Erro no resultado nacional (p.p.)
- Acerto do vencedor por UF
- Log score / CRPS do intervalo previsto (calibração: os 90% de intervalo cobrem ~90% dos casos?)

**Regra:** se o modelo não bater a persistência no backtest, não publica como "previsão".

Importante: o backtest do swing precisa receber o **δ real** (ou pesquisas da época) para separar "erro do δ" de "erro da distribuição entre UFs". Meça os dois separadamente.

---

## 6. Arquitetura sugerida (espelhando o Sassamaru)

| Sassamaru | Eleições |
|---|---|
| `datasets/*.csv` | `datasets/eleicoes-presidente-municipio.csv` |
| `fetch_xg.py` | `fetch_tse.py` (baixa, limpa, classifica blocos) |
| `modelos/model.js` | `modelos/eleicoes-model.js` (simulação, JS puro) |
| backtest walk-forward | `tests/backtest-eleicoes.js` (leave-one-election-out) |
| `apps/index.html` | `apps/eleicoes.html` |
| `i18n/` (en, zh) | mesma estrutura |
| `bench-docs.html` | seção de metodologia, com **limitações explícitas** |

**Divisão de trabalho que acho vantajosa:**

- **Python** (seu forte) faz ETL e **ajusta** o modelo (λ_i, σ, gaps) com `pandas` + `statsmodels` ou PyMC, e exporta um `parametros.json`.
- **JS** só carrega o JSON e roda o Monte Carlo no navegador, mantendo o projeto sem build e sem framework.

Assim você não precisa implementar inferência bayesiana em JS puro.

---

## 7. Plano em fases

| Fase | Entrega | Critério de pronto |
|---|---|---|
| 0 | `fetch_tse.py` + CSV 2014/2018/2022 (e 2002–2010 se der) por município | totais batem com o resultado oficial nacional |
| 1 | Baselines (persistência + swing uniforme) + backtest | tabela de erros por UF |
| 2 | Swing com sensibilidade regional + gaps das capitais | bate persistência no backtest |
| 3 | Camada de pesquisas (δ com incerteza) + Monte Carlo | probabilidades calibradas no backtest |
| 4 | Interface (tabelas e gráficos) + i18n + docs de metodologia | testes passando |

Se o objetivo for ter algo antes do 4/10: faça só as fases 0 e 1, congele e commite a previsão, e use o resto para o 2º turno.

---

## 8. Limitações para escrever na documentação

1. **Pouquíssimos dados**: 2–5 transições por unidade. Intervalos precisam ser largos.
2. **Falácia ecológica**: o modelo prevê agregados (município/UF), não explica por que alguém vota em alguém.
3. **Mudança de oferta**: candidatos e contexto mudam; o bloco "direita" de 2026 não é o de 2018 nem o de 2022.
4. **Terceira via no 1º turno**: o modelo de dois blocos perde informação quando há muita dispersão.
5. **Abstenção e comparecimento** variam e afetam o peso de cada UF; incluir cenário de comparecimento.
6. **Pesquisas têm viés sistemático** em alguns pleitos; não são verdade, são insumo.
7. **Não é pesquisa eleitoral.** Deixe claro no site que é um modelo estatístico baseado em dados históricos, não um levantamento de intenção de voto. Vale confirmar com atenção as regras do TSE/legislação eleitoral sobre divulgação de projeções antes de publicar (não sou advogado, então isso fica por sua conta checar).

---

## 9. Decisões que preciso de você

1. **Alvo:** 1º turno, 2º turno ou os dois? (Recomendo começar pelo 2º turno.)
2. **Bloco:** "anti-PT" (inclui 2014 e anos anteriores) ou "bolsonarista" (só 2018 e 2022)?
3. **Granularidade:** posso assumir município como base e agregar para UF/capital?
4. **Histórico:** topa incluir 2002–2010 para ter mais transições?
5. **Pesquisas:** inserção manual (um CSV de pesquisas que você atualiza) ou algum agregador?

# Sassamaru Eleições 2026 — pesquisas coletadas e decisões

Data da coleta: 1º de outubro de 2026 (3 dias antes do 1º turno, 4/10).

## 1. Decisões fechadas

| Tema | Decisão |
|---|---|
| Alvo | 1º e 2º turno |
| Bloco | **Anti-PT** (série contínua a partir de 2002) |
| Granularidade | Município como base, agregando para UF e capital |
| Histórico | 2002 em diante (2002, 2006, 2010, 2014, 2018, 2022) |
| Pesquisas | Só 4 institutos: Datafolha, Quaest, AtlasIntel, Real Time Big Data |

## 2. Arquivos

| Arquivo | Conteúdo |
|---|---|
| `datasets/pesquisas-2026.csv` | 25 rodadas (jun–out/2026), 1º e 2º turno, com metodologia, amostra e observações |
| `docs/pesquisas-2026-tendencia.png` | Gráfico: diferença Lula − Flávio no 1º turno e % de Lula no 2º turno simulado |

Colunas do CSV: `instituto, metodo, campo_ini, campo_fim, divulgacao, amostra, base, t1_*, t2_*, obs`.
`base` é `total` (sobre todos os entrevistados) ou `validos`. Células vazias significam "não localizei", não zero.

## 3. Última rodada de cada instituto

| Instituto | Método | Campo | Lula | Flávio | Lula entre os 2 (1º turno) | 2º turno (Lula x Flávio) |
|---|---|---|---|---|---|---|
| Datafolha | presencial | 22–23/set | 40 | 36 | 52,6% | último que achei: 46 x 44 (1–3/set) |
| Quaest | presencial | divulgada 28/set | 39 | 34 | 53,4% | último que achei: 42 x 41 (30/ago–1/set) |
| AtlasIntel | online | 23–28/set | 45,3 | 42,2 | 51,8% | 47,6 x 47,7 (50 x 50 em válidos) |
| Real Time Big Data | telefone | 26–30/set | 46 (válidos) | 41 (válidos) | 52,9% | 45 x 46 (49 x 51 em válidos) |

## 4. Tendência

A vantagem de Lula no 1º turno encolheu nos quatro institutos desde agosto:

| Instituto | Gap em meados de agosto | Gap na última rodada |
|---|---|---|
| AtlasIntel | 9,7 p.p. | 3,1 p.p. |
| Real Time Big Data | 8,0 p.p. | 5,0 p.p. |
| Quaest | 7,0 p.p. | 5,0 p.p. |
| Datafolha | 6,0 p.p. | 4,0 p.p. |

Na última semana, Quaest e Nexus mostraram Lula subindo de novo, enquanto o Atlas ficou estável. Ou seja: a tendência de queda parece ter parado, mas não dá para afirmar uma reversão com esses dados.

## 5. Pontos de atenção para o modelo

1. **Bases diferentes.** O Atlas deixa só ~1–2% de indecisos/brancos; Datafolha, Quaest e RTBD deixam 7–15%. Compare sempre em **participação entre os dois (Lula / (Lula + Flávio))** ou em votos válidos. A tabela da seção 3 já faz isso.
2. **House effects.** Atlas (online) concentra mais voto nos dois primeiros e tem Renan Santos mais alto; os presenciais têm mais indecisos. O modelo deve estimar um viés por instituto, não só fazer média.
3. **Viés histórico das pesquisas.** Em 2022, várias pesquisas superestimaram a vantagem do Lula no 1º turno. O desvio-padrão do swing nacional (δ) precisa incluir esse erro histórico.
4. **Flávio ≠ Jair.** O 2º turno está praticamente empatado em Atlas e RTBD. A transferência de voto do bolsonarismo é a maior incerteza do parâmetro δ.
5. **1º turno com terceira via.** Cury (~4–6%), Caiado (~2–4%) e Renan Santos (~3–6%) somam bastante. No 2º turno de 25/10, o destino desses votos vira parâmetro.

## 6. Lacunas e inconsistências (precisam de checagem manual)

| Item | Problema |
|---|---|
| Datafolha 2º turno de setembro | Não localizei |
| Quaest 2º turno de setembro | Não localizei |
| Quaest 28/set | Datas de campo e amostra não confirmadas |
| Datafolha 22–23/set | Wikipedia diz 22–24/set; data de divulgação diverge entre fontes (24 ou 28/set) |
| Datafolha 1–3/set | Wikipedia diz 1–2/set; há cenário com e sem Marçal (usei sem) |
| RTBD 19–23/set | Fontes divergem: Lula 44 ou 45 no 2º turno |
| RTBD 26–30/set | Base em válidos; Renan Santos não listado (soma 97) |
| Atlas 23–28/set | Só encontrei Lula e Flávio no 1º turno |

Boa parte dos números veio da tabela da Wikipedia sobre pesquisas de 2026 e de reportagens (Gazeta do Povo, CNN Brasil, CartaCapital). Antes de usar no modelo, vale conferir contra os PDFs registrados no TSE (cada pesquisa tem um número de registro BR-xxxxx/2026).

## 7. Como isso entra no modelo

```
δ_2026 (swing nacional, em logit do % de Lula entre os dois)
  = média ponderada das 4 casas, com
    - peso por recência (decaimento exponencial)
    - peso por amostra
    - correção de house effect por instituto
  + incerteza = erro amostral + viés histórico das pesquisas + variância entre institutos
```

O δ é aplicado ao resultado de 2022 de cada município com a sensibilidade λ regional estimada no histórico 2002–2022 (ver `docs/sassamaru-eleicoes-plano.md`).

## 8. Próximo passo

Fase 0 do plano: `fetch_tse.py` para baixar votação por município (2002–2022) e montar o CSV histórico. O TSE não está entre os domínios que consigo acessar no ambiente onde rodo código, então esse script teria de ser executado na sua máquina. Posso escrever e deixar pronto para você rodar.

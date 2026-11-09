# Resultados Comparativos — Classificador de Assuntos (Entrega 2 IA)

**Data:** 2026-11-08 13:50

## Dados de Treinamento

- Fonte: `Relacionamentos.xlsx` (96.628 registros, 294 motivos únicos)
- Excluídos: motivos AMBÍGUO (9) e NÃO_ASSUNTO (3) conforme plano
- Split: `StratifiedKFold(5)` sobre motivos únicos + hold-out 20% fixo
- Vetorização: `TfidfVectorizer(analyzer='char_wb', ngram_range=(2,4), sublinear_tf=True)`

## Cross-Validation (5 Folds — sobre motivos únicos)

| Modelo | Accuracy | Precision (macro) | Recall (macro) | F1-macro |
|---|---|---|---|---|
| Regressao Logistica | 0.7552 ± 0.0243 | 0.7897 ± 0.0257 | 0.7740 ± 0.0244 | 0.7677 ± 0.0274 |
| Arvore de Decisao | 0.5104 ± 0.0319 | 0.5470 ± 0.0694 | 0.5135 ± 0.0426 | 0.5010 ± 0.0478 |

## Hold-out 20% (Fixo — avaliação independente)

| Modelo | Accuracy | Precision (macro) | Recall (macro) | F1-macro |
|---|---|---|---|---|
| Regressao Logistica | 0.7627 | 0.7592 | 0.7867 | 0.7547 |
| Arvore de Decisao | 0.4576 | 0.5402 | 0.4930 | 0.4787 |

**Melhor modelo (F1-macro no hold-out):** Regressao Logistica

## Matrizes de Confusão (Hold-out)

### Regressao Logistica

```
Classes: Atendimento Geral e  | Carteirinha e Transp | Documentação Acadêmi | Estágio, Carreira e  | Financeiro, Bolsas e | Matrícula, Rematrícu | Portal e Sistemas | Vida Acadêmica e Ava
[[ 8  0  0  0  1  0  1  0]
 [ 0  3  0  0  0  0  0  0]
 [ 0  0  4  2  0  0  0  1]
 [ 1  0  0  3  1  0  0  1]
 [ 0  0  0  0 13  2  0  0]
 [ 0  0  0  0  0  5  0  0]
 [ 0  0  0  0  0  0  4  0]
 [ 0  1  0  2  0  1  0  5]]
```

### Arvore de Decisao

```
Classes: Atendimento Geral e  | Carteirinha e Transp | Documentação Acadêmi | Estágio, Carreira e  | Financeiro, Bolsas e | Matrícula, Rematrícu | Portal e Sistemas | Vida Acadêmica e Ava
[[2 0 1 2 0 1 1 3]
 [0 2 1 0 0 0 0 0]
 [0 0 4 3 0 0 0 0]
 [0 0 0 3 0 0 0 3]
 [0 0 1 3 6 2 1 2]
 [0 0 0 0 1 4 0 0]
 [1 0 0 0 0 0 1 2]
 [0 0 1 1 1 0 1 5]]
```

## Limitações

- O classificador opera sobre textos de **motivos padronizados** (319 variações), não sobre linguagem livre.
- Desempenho em perguntas livres dos alunos pode ser inferior — ver `analise_erros.md`.
- Categorias com poucos motivos únicos (Carteirinha: 13, Portal: 21) têm menor representatividade.
- Rótulos foram atribuídos por regras auditáveis, sem validação humana independente nesta versão.
- Métricas apresentadas são de **teste técnico** (hold-out), não de validação humana.

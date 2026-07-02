# Fluxo do Compiler

O Terbie Compiler cria uma representacao intermediaria analitica antes do plano
de execucao.

```text
Natural Language Question
    ↓
SemanticResolution
    ↓
KnowledgeContext
    ↓
AnalyticalHypothesis
    ↓
AnalyticalPlan
    ↓
ExecutionPlan
```

## AnalyticalHypothesis

Representa a hipotese sobre o que o usuario quer descobrir.

Exemplos:

- tipo de analise: ranking;
- metrica principal: faturamento;
- entidade de negocio: restaurante;
- escopo temporal: mes atual.

## AnalyticalPlan

Representa uma visao intermediaria analitica, ainda independente da execucao.
Define entidades, metricas, dimensoes, filtros e operacoes requeridas.

## ExecutionPlan

E o contrato que sera consumido futuramente pelo Executor. Ele contem operacoes
declarativas como `group_by`, `aggregate`, `sort` e `limit`.

Na fase atual, `is_executable` permanece `false`, pois ainda nao existe Executor
real nem validacao completa contra colunas fisicas.

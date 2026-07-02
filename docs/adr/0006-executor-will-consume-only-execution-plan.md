# ADR 0006: Executor Consumira Somente ExecutionPlan

## Status

Accepted

## Contexto

O Executor nao deve interpretar linguagem natural nem depender de LLM. Sua
responsabilidade sera executar instrucoes declarativas.

## Decisao

O futuro Executor consumira somente `ExecutionPlan` validado.

## Consequencias

O Executor fica deterministico, testavel e independente de provider de IA. O
Planner e o Compiler carregam a responsabilidade de traducao analitica.

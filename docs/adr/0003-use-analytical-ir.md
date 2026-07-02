# ADR 0003: Usar Representacao Intermediaria Analitica

## Status

Accepted

## Contexto

Transformar linguagem natural diretamente em plano executavel cria acoplamento e
dificulta depuracao.

## Decisao

Introduzir uma IR analitica composta por `AnalyticalHypothesis` e
`AnalyticalPlan` antes do `ExecutionPlan`.

## Consequencias

O fluxo fica mais explicavel e auditavel. O projeto pode trocar partes
deterministicas por LLM no futuro sem alterar o Executor.

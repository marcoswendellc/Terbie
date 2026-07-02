# ADR 0001: Usar Clean Architecture

## Status

Accepted

## Contexto

O Terbie precisa evoluir em varias frentes: API, dados, semantica, conhecimento,
compiler, executor, LLM e narracao. Misturar essas responsabilidades tornaria o
sistema dificil de testar e manter.

## Decisao

Adotar Clean Architecture com camadas claras e dependencias direcionadas para
contratos internos.

## Consequencias

O sistema fica mais modular, testavel e preparado para substituir implementacoes
sem quebrar contratos. Em troca, ha mais arquivos e mais disciplina de injecao
de dependencias.

# ADR 0002: LLM Nao Acessa Dados Brutos

## Status

Accepted

## Contexto

O Terbie lidara com dados sensiveis e informacoes de negocio. Enviar dados
brutos para uma LLM aumentaria risco de privacidade, custo e comportamento nao
auditavel.

## Decisao

A LLM podera receber apenas pergunta, schema, catalogo, resolucao semantica,
conhecimento de negocio e contratos declarativos. Ela nunca recebera DataFrames,
tabelas completas, credenciais ou resultados reais.

## Consequencias

A arquitetura preserva seguranca e auditabilidade. O Executor sera responsavel
por executar planos, nao a LLM.

# ADR 0002: LLM Nao Acessa Dados Brutos

## Status

Accepted — esclarecido em 2026-09-28 para narrativa e direção conversacional.

## Contexto

O Terbie lidara com dados sensiveis e informacoes de negocio. Enviar dados
brutos para uma LLM aumentaria risco de privacidade, custo e comportamento nao
auditavel.

## Decisao

A LLM de planejamento recebe pergunta, schema, catálogo, resolução semântica,
conhecimento de negócio e contratos declarativos. A narrativa, a direção da conversa
e as sugestões podem receber resultados calculados após verificação e sanitização,
assim como o histórico dessas respostas. Não recebem DataFrames, tabelas brutas
completas ou credenciais. A narrativa recebe até 50 linhas calculadas por contexto;
o diretor usa até 20 linhas de cada turno recente e as sugestões até 50 por análise.

Esta revisão explicita o uso de resultados governados que o narrador já fazia e
aplica a mesma ordem de governança às consultas compostas. Valores de negócio são
calculados pelo executor; a LLM escolhe análises e apresenta seus resultados.

## Consequencias

A arquitetura preserva seguranca e auditabilidade. O Executor sera responsavel
por executar planos, nao a LLM.

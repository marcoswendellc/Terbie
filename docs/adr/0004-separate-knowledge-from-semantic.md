# ADR 0004: Separar Knowledge de Semantic

## Status

Accepted

## Contexto

Sinonimos e parametros de linguagem natural sao diferentes de regras formais de
negocio, metricas oficiais e hierarquias.

## Decisao

Manter `semantic/` para interpretacao textual e `knowledge/` para conhecimento
formal de negocio.

## Consequencias

As camadas podem evoluir separadamente. O conhecimento de negocio fica
versionavel, testavel e reutilizavel pelo Compiler e futuros providers.

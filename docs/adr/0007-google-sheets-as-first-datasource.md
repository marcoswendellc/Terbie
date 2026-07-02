# ADR 0007: Google Sheets Como Primeira Fonte de Dados

## Status

Accepted

## Contexto

O projeto precisava validar uma fonte real rapidamente, com baixo atrito e dados
ja disponiveis em planilhas.

## Decisao

Implementar Google Sheets como primeiro datasource real, usando service account
e `gspread`.

## Consequencias

O Terbie consegue ler dados reais e descobrir schemas. A arquitetura preserva a
possibilidade de adicionar SQL, APIs e outras fontes no futuro.

# Fluxo de Dados

O fluxo de dados atual separa leitura, descoberta estrutural e planejamento.

```text
Google Sheets
    ↓
DataSource
    ↓
Schema Discovery
    ↓
Data Catalog
    ↓
Knowledge / Semantic / Compiler
    ↓
Future Executor
```

## Google Sheets

O Google Sheets e a primeira fonte real do Terbie. A autenticacao usa service
account via variavel de ambiente `GOOGLE_SERVICE_ACCOUNT_JSON`.

## DataSource

O datasource le abas como DataFrames e entrega dados tabulares para os servicos
de dados. Ele nao contem regras de negocio.

## Schema Discovery

Identifica colunas, tipos, nulos, exemplos e estatisticas basicas. O resultado
e armazenado como schema estruturado.

## Data Catalog

Mantem a memoria estrutural dos dados carregados. O catalogo informa quais
tabelas existem e qual e o schema de cada tabela.

## Uso Pelo Planner

O Planner e o Compiler podem receber schemas e metadados, mas nunca dados brutos.

## Regra de Seguranca

Dados brutos nunca sao enviados para LLM. Credenciais, chaves privadas, tabelas
completas, DataFrames e resultados reais de consultas tambem sao proibidos no
contexto de raciocinio.

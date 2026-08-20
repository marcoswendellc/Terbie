# Terbie

Terral BI Copilot Engine: agente analítico conversacional com planejamento
declarativo, execução determinística, verificação e governança.

## Arquitetura

O Terbie e um motor analitico conversacional orientado por contratos. Ele separa
interpretacao semantica, conhecimento de negocio, compilacao analitica,
planejamento e futura execucao.

Documentos principais:

- [Visao geral da arquitetura](docs/architecture/overview.md)
- [Planner Specification v1](docs/planner-specification-v1.md)
- [Architecture Decision Records](docs/adr/)

## Capacidades atuais

- resolução semântica e índice de valores dimensionais;
- filtros simples e expressões booleanas aninhadas (`AND`/`OR`);
- métricas, rankings, comparações, personas e consultas compostas;
- estatística descritiva, participação e detecção de outliers por IQR;
- ciclo limitado `planejar → executar → verificar → reparar`;
- rastreamento de duração e quantidade de linhas por operação;
- cache de dados, memória em processo ou SQLite e política de grupo mínimo;
- narrativa determinística para fatos e LLM opcional para interpretação.

## Configuração operacional

```text
DATA_CACHE_TTL_SECONDS=60
MINIMUM_ANALYTICAL_GROUP_SIZE=1
MEMORY_BACKEND=memory            # ou sqlite
MEMORY_SQLITE_PATH=.terbie/memory.db
LOCAL_DATA_PATH=./dados              # diretório CSV ou arquivo Excel
AUTH_REQUIRED=false                  # em produção é sempre obrigatório
SESSION_SECRET=troque-este-segredo
SESSION_TTL_SECONDS=28800
ALLOWED_SHOPPINGS=                    # lista opcional separada por vírgulas
```

Em produção, recomenda-se `MINIMUM_ANALYTICAL_GROUP_SIZE=5` ou superior.

## Dependencias

O provider Gemini usa o pacote `google-genai`.

```powershell
pip install google-genai
```

## Releases

- [v0.1.0 — Foundation](docs/releases/v0.1.0.md)

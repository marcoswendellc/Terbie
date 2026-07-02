# Visao Geral da Arquitetura

O Terbie e um motor analitico conversacional. Ele nao deve ser tratado como um
chatbot generico: sua responsabilidade e transformar perguntas de negocio em
representacoes analiticas auditaveis, seguras e executaveis por componentes
especializados.

O sistema ainda nao responde perguntas finais, nao executa consultas e nao chama
LLM real. A arquitetura atual prepara o caminho para que essas capacidades sejam
adicionadas sem misturar responsabilidades.

## Fluxo Conceitual

```text
User Question
    ↓
FastAPI
    ↓
Orchestrator
    ↓
Semantic Resolution
    ↓
Knowledge Context
    ↓
Compiler
    ↓
Analytical Hypothesis
    ↓
Analytical Plan
    ↓
Execution Plan
    ↓
Future Executor
    ↓
Future Narrator
```

## Papel da LLM

A LLM sera apenas uma implementacao de `ReasoningProvider`.

Ela podera apoiar raciocinio e planejamento, mas nao tera acesso a dados brutos,
credenciais, DataFrames completos, tabelas inteiras ou resultados reais de
consulta. A LLM devera trabalhar somente com pergunta, schemas, catalogo,
semantica, conhecimento de negocio e contratos declarativos.

## Principio Central

O Terbie separa explicitamente:

- interpretacao da pergunta;
- conhecimento de negocio;
- hipotese analitica;
- plano analitico;
- plano de execucao;
- execucao futura;
- narracao futura.

Essa separacao preserva auditabilidade, testabilidade e evolucao segura.

# Visao Geral da Arquitetura

O Terbie e um motor analitico conversacional. Ele nao deve ser tratado como um
chatbot generico: sua responsabilidade e transformar perguntas de negocio em
representacoes analiticas auditaveis, seguras e executaveis por componentes
especializados.

O sistema responde perguntas, executa planos sobre fontes tabulares e pode usar
uma LLM como apoio controlado de raciocinio e narracao. Calculos factuais continuam
deterministicos e auditaveis.

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
Executor
    ↓
Verifier
    ↓
Narrator
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
- execucao deterministica;
- verificacao e reparo limitado;
- narracao factual e interpretativa.

Essa separacao preserva auditabilidade, testabilidade e evolucao segura.

## Ciclo do agente

Consultas analiticas podem usar um ciclo limitado de planejamento, execucao,
verificacao e reparo. A verificacao cobre preservacao de filtros, percentuais,
valores predominantes e resultados vazios. O limite de reparos impede loops
autonomos sem controle.

## Governanca

O runtime remove campos sensiveis da saida, permite configurar tamanho minimo de
grupo analitico, bloqueia tabelas restritas e registra rastreamento por operacao.

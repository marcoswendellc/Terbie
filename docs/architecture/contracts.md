# Contratos Principais

## SemanticResolution

Resultado da camada semantica. Contem a pergunta original, a pergunta
normalizada, termos reconhecidos, parametros extraidos, warnings e confianca.

## KnowledgeContext

Consolida entidades, metricas, dimensoes, regras, hierarquias, calendarios e
taxonomias de negocio.

## CompilerRequest

Entrada do Terbie Compiler. Reune pergunta, resolucao semantica, conhecimento de
negocio e contexto opcional de schema.

## CompilerResponse

Saida do Terbie Compiler. Contem pergunta, hipotese analitica, plano analitico,
plano de execucao, warnings e status.

## AnalyticalHypothesis

Hipotese sobre o objetivo analitico do usuario. Ajuda a separar entendimento da
pergunta de construcao de plano.

## AnalyticalPlan

Representacao intermediaria com intencao, entidades, metricas, dimensoes,
escopo temporal, filtros e operacoes requeridas.

## ExecutionPlan

Plano declarativo que sera consumido futuramente pelo Executor. Nao contem dados
brutos nem resultados de consulta.

## ReasoningContext

Contexto seguro enviado a um `ReasoningProvider`. Pode conter pergunta,
semantica, schema, catalogo e conhecimento de negocio.

## ReasoningResult

Resultado produzido por um `ReasoningProvider`. No momento, o provider mockado
retorna um `ExecutionPlan` deterministico.

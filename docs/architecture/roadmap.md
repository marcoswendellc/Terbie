# Roadmap

## Sprint 8: Domain Layer

Formalizar dominios analiticos, vocabulos e contratos de negocio por area.

## Sprint 9: Logical Query Plan

Introduzir um plano logico intermediario entre `ExecutionPlan` e execucao fisica.

## Sprint 10: Executor Architecture

Definir arquitetura do Executor, contratos de entrada e saida, erros e
validacoes.

## Sprint 11: Gemini ReasoningProvider

Implementar provider real de raciocinio com Gemini, mantendo a abstracao
`BaseReasoningProvider`.

## Sprint 12: Pandas Executor

Criar executor inicial baseado em Pandas para executar `ExecutionPlan` validado.

## Sprint 13: Narrator

Criar camada responsavel por explicar resultados ao usuario sem executar dados.

## Sprint 14: RAG/Memory

Adicionar memoria e recuperacao contextual com governanca de dados.

## Sprint 15: Agents/MCP

Introduzir agentes e MCP somente apos contratos de planejamento e execucao
estarem estabilizados.

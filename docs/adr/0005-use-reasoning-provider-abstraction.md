# ADR 0005: Usar Abstracao de Reasoning Provider

## Status

Accepted

## Contexto

O Terbie devera suportar provedores como Gemini, OpenAI, Claude, Ollama e modelos
locais. Acoplar o Planner a um unico fornecedor criaria dependencia prematura.

## Decisao

Criar `BaseReasoningProvider` como porta abstrata e usar `MockReasoningProvider`
enquanto nao houver LLM real.

## Consequencias

A troca de provider fica isolada. Testes continuam deterministicos e nenhuma
chamada externa de IA e necessaria nas sprints iniciais.

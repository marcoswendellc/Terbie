# Camadas

Este documento descreve as responsabilidades das principais camadas do Terbie.

## api/

Recebe requisicoes HTTP e converte payloads em chamadas a services ou
orchestrators. Nao contem logica de negocio.

## orchestrator/

Coordena o fluxo principal da aplicacao. No estado atual, recebe a pergunta,
aciona a resolucao semantica, obtem conhecimento de negocio e chama o Planner.

## semantic/

Reconhece termos, sinonimos, intencoes e parametros em linguagem natural. Essa
camada e deterministica e nao chama LLM.

## knowledge/

Define conhecimento formal de negocio: entidades, metricas, dimensoes, regras,
calendarios, taxonomias e hierarquias.

## compiler/

Transforma pergunta, semantica e conhecimento em:

- `AnalyticalHypothesis`;
- `AnalyticalPlan`;
- `ExecutionPlan`.

O compiler nao executa dados.

## planner/

Contem modelos e contratos do plano, parser, validator, optimizer e estruturas
de contexto. A Sprint 6 tornou o compiler o caminho principal para criar planos.

## reasoning/

Abstrai provedores de raciocinio, como Gemini, OpenAI, Claude, Ollama ou modelos
locais. O provider atual e mockado e deterministico.

## datasources/

Conecta fontes de dados. A primeira fonte implementada e Google Sheets.

## catalog/

Armazena schemas descobertos e metadados estruturais das tabelas carregadas.

## future executor/

Executara somente `ExecutionPlan`. Nao interpretara linguagem natural e nao
chamara LLM.

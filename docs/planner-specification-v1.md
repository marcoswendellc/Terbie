# Terbie — Planner Specification v1.0

## 1. Objetivo

O Planner é o componente responsável por transformar uma pergunta em linguagem natural em um plano analítico declarativo.

O Planner não executa consultas, não acessa dados brutos e não responde ao usuário final.

Ele apenas gera um `ExecutionPlan`.

---

## 2. Princípio central

A LLM nunca deve acessar os dados.

Ela pode receber:

* pergunta do usuário;
* schema das tabelas;
* catálogo de dados;
* resolução semântica;
* regras de negócio;
* exemplos de operações disponíveis.

Ela nunca pode receber:

* DataFrame completo;
* dados sensíveis;
* tabelas inteiras;
* resultados reais de consulta;
* credenciais;
* chaves privadas.

---

## 3. Fluxo do Planner

```text
User Question
    ↓
Semantic Resolution
    ↓
Schema Context
    ↓
Data Catalog Context
    ↓
Context Composer
    ↓
Reasoning Provider
    ↓
ExecutionPlan
    ↓
Plan Validator
    ↓
Plan Optimizer
```

---

## 4. Responsabilidades

### Planner

Responsável por coordenar a criação do plano.

Não deve conter regra específica de Google Sheets, Pandas, Gemini ou FastAPI.

### Context Composer

Responsável por montar o contexto enviado ao Reasoning Provider.

### Reasoning Provider

Interface abstrata para modelos de IA.

Implementações futuras:

* Gemini
* OpenAI
* Claude
* Ollama
* modelos locais

### Plan Validator

Valida se o plano gerado é estruturalmente seguro.

### Plan Optimizer

Otimiza o plano antes da execução.

---

## 5. ExecutionPlan

Formato oficial:

```json
{
  "version": "1.0",
  "intent": "ranking",
  "entities": [],
  "metrics": [],
  "parameters": [],
  "operations": [],
  "warnings": [],
  "is_executable": false
}
```

---

## 6. Regras obrigatórias

O Planner deve:

* gerar apenas planos declarativos;
* usar somente colunas existentes no schema;
* usar somente operações suportadas;
* indicar `is_executable=false` quando houver ambiguidade;
* adicionar warnings quando faltar informação;
* nunca inventar métricas, colunas ou valores;
* nunca estimar números;
* nunca responder com base em conhecimento próprio.

---

## 7. Operações suportadas inicialmente

* select
* filter
* group_by
* aggregate
* sort
* limit
* compare_periods
* growth
* rank
* share
* trend
* outlier

Operações futuras:

* forecast
* pivot
* unpivot
* join
* rolling_sum
* moving_average
* cumulative_sum

---

## 8. Exemplo

Pergunta:

```text
Quais são os 10 restaurantes com maior faturamento este mês?
```

Plano esperado:

```json
{
  "version": "1.0",
  "intent": "ranking",
  "entities": [
    {
      "name": "restaurante"
    }
  ],
  "metrics": [
    {
      "name": "faturamento",
      "aggregation": "sum"
    }
  ],
  "parameters": [
    {
      "type": "limit",
      "value": 10
    },
    {
      "type": "period",
      "value": "current_month"
    }
  ],
  "operations": [
    {
      "type": "filter",
      "function": null,
      "field": "data",
      "alias": null,
      "parameters": {
        "period": "current_month"
      }
    },
    {
      "type": "group_by",
      "function": null,
      "field": "restaurante",
      "alias": null,
      "parameters": {}
    },
    {
      "type": "aggregate",
      "function": "sum",
      "field": "valor",
      "alias": "faturamento",
      "parameters": {}
    },
    {
      "type": "sort",
      "function": null,
      "field": "faturamento",
      "alias": null,
      "parameters": {
        "direction": "desc"
      }
    },
    {
      "type": "limit",
      "function": null,
      "field": null,
      "alias": null,
      "parameters": {
        "value": 10
      }
    }
  ],
  "warnings": [],
  "is_executable": true
}
```

---

## 9. Casos de ambiguidade

Se o usuário perguntar:

```text
Qual loja vendeu mais?
```

E houver mais de uma coluna possível para vendas, o Planner deve retornar:

```json
{
  "warnings": [
    "Não foi possível identificar com segurança qual coluna representa faturamento."
  ],
  "is_executable": false
}
```

---

## 10. Critérios de qualidade

Um bom plano deve ser:

* válido;
* auditável;
* determinístico;
* explicável;
* seguro;
* independente da fonte de dados;
* executável por Python, não pela LLM.

---

## 11. Regra final

O Planner pensa.

O Executor executa.

O Narrator explica.

Nenhuma camada deve assumir a responsabilidade da outra.

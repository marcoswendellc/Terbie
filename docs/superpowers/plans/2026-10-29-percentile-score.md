# Percentile score implementation plan

> Execute inline with superpowers:executing-plans; verify each task with tests.

**Goal:** calcular e explicar score composto para lojas, clientes e bairros.
**Architecture:** reconhecimento determinístico → filtro existente → agregação
de compras canônicas → percentis e média ponderada → ranking e narrativa.
**Tech stack:** Python, pandas, pytest, interface de tabelas existente.
**Spec:** ../specs/2026-10-29-percentile-score-design.md

## Constraints and review focus

- Pesos iguais por padrão, positivos ou zero, soma positiva e configuração validada.
- Filtrar antes de calcular; top N depois. Métrica explícita vence score implícito.
- Empates, entidade única, dados ausentes e compras duplicadas devem ser testados.
- Preservar shoppings autorizados e identidades separadas entre lojas e bairros.
- Não expor identificadores brutos de clientes; não inventar valores ausentes.

## Tasks

- [x] 1. Testar e implementar função de percentis e pesos em
  `app/executor/operations/business_score.py` e definição em
  `app/knowledge/scoring.py`; testes em `tests/test_business_score.py`.
- [x] 2. Testar e implementar reconhecimento em `app/semantic/scoring.py`,
  integração em `business_analysis.py`, compilador e operação existente;
  testes de ponta a ponta em `tests/test_business_score_flow.py`.
- [x] 3. Registrar regra/métrica de negócio e narrativa transparente;
  verificar casos explícitos, escopo, top N, governança e ausência de dados.
- [x] 4. Executar suíte completa, lint dos arquivos alterados e revisão final.

## Execution ledger

Preparação: repositório sem alterações de usuário ao iniciar; manter o checkout
compartilhado utilizado nas mudanças anteriores. Sem publicação ou commit manual.

Etapa 1: testes reproduziram ausência do cálculo; função passou com percentis
normalizados, pesos configuráveis, empates e entidade única. Score preserva 12
casas para ordenar empates numéricos de forma estável e exibe 2 casas na narrativa.

Etapas 2–3: testes das perguntas originais falharam antes da integração e passaram
depois. Verificados critério explícito, top N sem mudar percentis, nomes iguais
em shoppings/cidades diferentes, compras duplicadas, período vazio, referências
anônimas e fonte autorizada. Regra de mínimo de clientes aplicada antes de score
e top N, preservando a política de saída existente.

Verificação inicial: 646 testes passaram e lint dos arquivos alterados passou.
Revisão final independente solicitada; publicação não executada.

Revisão final: corrigidos e testados cinco achados sobre filtros de loja,
identidade canônica, alvo versus dimensão de filtro, campos ausentes e critério
por número de clientes. Revisão independente confirmou as correções sem novos
impedimentos; 31 testes focados passaram. Suíte final: 651 testes passaram.
Os pesos são configuráveis em `app/knowledge/scoring.py` e via parâmetro interno
`score_weights` da operação. Mantidos sem alteração os padrões de outros rankings
(por exemplo, melhor campanha); score padrão introduzido nos três tipos aprovados.

# Investigação conversacional — plano de implementação

**Goal:** integrar iniciativa analítica, sugestões executáveis e continuidade ao chat.
**Architecture:** diretor opcional compõe perguntas sobre o executor existente;
memória registra decisões e sugestões; UI permite escolher ou escrever livremente.
**Tech Stack:** Python, Pydantic, FastAPI, Gemini SDK existente, JavaScript nativo.
**Spec:** `docs/superpowers/specs/2026-09-28-conversational-analysis-design.md`.

## Restrições globais
- Preservar mudanças locais e contratos existentes; nenhum novo framework.
- Até três análises e duas sugestões; prazo cooperativo de 60 segundos.
- Não ler `.env`, enviar dados brutos ou executar sugestões antes da escolha.

## Foco de revisão
- Referência ambígua entre sugestões: pedir esclarecimento, sem escolher ao acaso.
- Mudança explícita de shopping: não reaplicar filtros antigos.
- Falha de parte das consultas: preservar resultados válidos e indicar a falha.
- Campos sensíveis: remover antes de qualquer narrativa, inclusive multiquery.
- Provider indisponível: resposta útil pelo fluxo anterior, sem loop de tentativas.

## Tarefas
- [x] Contratos e memória: testes de seleção, persistência SQLite e isolamento;
  implementar sugestões tipadas e estado da investigação.
- [x] Diretor: testes de decisões, limites, schema e provider; implementar contrato
  de decisão Gemini e composição limitada sobre callback analítico.
- [x] Integração: testes numéricos de conversas e governança; conectar `/execute`,
  preservar consultas compostas na memória e sanitizar antes da narrativa.
- [x] Chat e documentação: apresentar premissas/sugestões, ações clicáveis, alinhar
  contrato de dados da LLM e executar suite completa e revisão final.

## Registro
- Exploração: cinco arquivos já modificados pelo usuário; preservar suas mudanças.
- Decisão: execução neste checkout para incluir o estado local aprovado pelo usuário.
- Validação inicial iniciada com leitura automática de `.env` desativada.
- Ambiente global: 280 passaram, três falharam por urllib3 incompatível com Python
  global. Os mesmos três passaram na venv; todos os testes seguintes usam a venv.
- Dependência existente implícita: teste Excel falhou por ausência de openpyxl na
  venv. Instalado openpyxl 3.1.5 e declarado no projeto para tornar o suporte
  existente reproduzível. Nenhuma credencial foi lida para os testes.
- Contratos/memória: onze falhas iniciais esperadas por recurso ausente; resolvidas.
- Integração: testes numéricos com 2.266 em compras e ticket 2.266/13, governança
  anterior à narrativa composta, referência por rótulo/ordinal e falha do provider.
- Chat: três testes Node inicialmente falharam; passaram após ações e premissas.
- Revisão independente concluída: corrigidos bloqueio prematuro de perguntas
  contextuais, validação de dependências reais de sugestões e propagação do prazo
  às chamadas Gemini internas. Cada correção possui teste de regressão.
- Validação final: 310 testes Python e quatro testes Node passaram; Ruff passou
  nos arquivos Python tocados. Único aviso: depreciação interna do SDK Google.
- Execução sem commit/push para preservar o trabalho local não commitado do usuário.
- Não foi feita chamada real a Gemini/Google Sheets; testes usam fontes sintéticas,
  cliente SDK simulado e leitura de `.env` desativada. Validação de entendimento
  linguístico com o modelo real permanece uma etapa operacional.
- Comandos de validação: `node --test tests/test_chat_conversation.cjs` e
  `venv/Scripts/python.exe -c "from app.core.config import Settings; Settings.model_config['env_file']=None; import pytest; raise SystemExit(pytest.main(['-q']))"`.

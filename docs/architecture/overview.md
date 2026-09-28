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

Ela pode apoiar raciocínio e planejamento sem acesso a dados brutos, credenciais,
DataFrames ou tabelas completas. O planejamento usa pergunta, schemas, catálogo,
semântica, conhecimento de negócio e contratos declarativos. A direção da conversa,
a narrativa e as sugestões podem receber resultados calculados e sanitizados e o
histórico dessas respostas. Governança e verificação precedem a narrativa.

Com Gemini, `/execute` usa um diretor conversacional para escolher até três análises
necessárias à pergunta atual e apresentar suas premissas. Depois, oferece até duas
sugestões compatíveis com o schema, que só são executadas após escolha do usuário.
As perguntas resolvidas e sugestões são registradas por sessão. O prazo de 60 segundos
é cooperativo: impede iniciar novas etapas, sem interromper operações pandas em curso.
Sem Gemini ou em falha de direção, permanece o fluxo analítico tradicional.

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

## Fonte semantica canonica

`app/semantic_kb` e a fonte canonica de metricas, dimensoes, intencoes, regras,
sinonimos e exemplos. `KnowledgeService` projeta esse catalogo para os contratos
de negocio e mantem apenas adaptadores de compatibilidade para definicoes
legadas. Novos conceitos devem ser cadastrados exclusivamente no catalogo
canonico.

## Avaliacoes de linguagem

Perguntas reais e seus contratos esperados ficam versionados em
`evals/business_questions.json`. O avaliador verifica intencao, formato e
contextos resolvidos, complementando os testes unitarios tradicionais.

## Ciclo do agente

Consultas analiticas podem usar um ciclo limitado de planejamento, execucao,
verificacao e reparo. A verificacao cobre preservacao de filtros, percentuais,
valores predominantes e resultados vazios. O limite de reparos impede loops
autonomos sem controle.

## Governanca

O runtime remove campos sensiveis da saida, permite configurar tamanho minimo de
grupo analitico, bloqueia tabelas restritas e registra rastreamento por operacao.

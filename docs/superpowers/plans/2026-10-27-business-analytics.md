# Ampliação das análises de negócio

**Objetivo:** responder deterministicamente às 20 perguntas fornecidas, mantendo as capacidades existentes. A comparação inferencial por gênero já existe; as outras 19 intenções terão operações dedicadas sobre compras registradas.

**Contrato:** módulos recebem DataFrame preparado, modo, ExecutionContext e opções. Retornam tabela agregada, sem identificadores de clientes. `context.metadata['business_analysis']` contém modo, notas e qualidade. Campos canônicos preservados; `__purchase` identifica uma compra (shopping + cd_compra). Linhas duplicadas são removidas; compras com valores conflitantes são excluídas e reportadas. Frequência = compras únicas/clientes únicos; ticket por compra e gasto por cliente são distintos. Campanha = shopping + identificador da promoção, com nomes visíveis. Percentuais têm denominador explícito; participações de clientes entre grupos podem se sobrepor.

**Estrutura:** reconhecimento e escopo em app/semantic/business_analysis.py; limpeza e agregação em app/executor/operations/business_common.py; despacho em business_analysis.py. Cálculos separados em business_customers.py (2,3,5,7,8,9,10,11,12), business_segments.py (13–18) e business_temporal.py (1,4,19,20). Narrativa determinística em app/narrator/business_analysis.py.

**Limites:** registros de compra não medem atração causal, fluxo total nem visitas sem compra. Faixa etária calculada na data da análise, com ausências reportadas. Datas inválidas não entram nas séries. Início/meio/fim usam três intervalos de duração equivalente dentro da vigência de cada campanha, sem substituir pelas datas observadas das compras. Concentração dos 10% usa ceil(0,10*N), com empates e contagem explicitados. Retenção usa identificação estável do cliente, compara campanhas ordenadas por início e não sugere causalidade. Pergunta 11 requer cidade do shopping explícita, nunca inferida dos clientes.

- [x] Testes reproduzíveis para reconhecimento das 20 perguntas e filtros.
- [x] Infraestrutura comum e integração no compilador, registro e narrativa.
- [x] Cálculos de clientes, geografia e segmentos com testes numéricos.
- [x] Cálculos temporais, fases e participação entre campanhas com testes.
- [x] Cadastro explícito opcional de cidades de shopping e resposta para ausência.
- [x] Suíte completa, lint, revisão e documentação das limitações.

Validação final: 576 testes Python e 11 testes da interface aprovados. Ruff aprovado nos arquivos alterados e novos; git diff --check aprovado. Revisões independentes dos cálculos e da integração concluídas. Testes com dados sintéticos; sem publicação ou validação da base conectada. O cadastro dos oito municípios foi incorporado com UF. Os dados de origem são restringidos aos shoppings autorizados antes das agregações.

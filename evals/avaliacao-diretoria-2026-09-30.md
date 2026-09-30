# Avaliação do Terbie sob a perspectiva de um diretor da Terral

**Parecer: útil para consultas específicas com conferência, mas ainda não confiável para decisões executivas sem revisão humana.** O maior problema é aceitar um recorte incorreto e apresentar um número plausível como resposta.

Avaliação em 30/09/2026: 15 perguntas reais ao serviço da versão local atual, usando as integrações configuradas e Google Sheets atualizado. Não é um teste do site publicado no Vercel. Base: **236.728 registros, 11 shoppings e 38 combinações de campanha/shopping**. Não alterei o comportamento do produto durante esta avaliação.

**Resultado desta amostra: 3 de acordo, 4 parciais e 8 que não atendem.** Não representa taxa estatística de acerto do produto. Cada avaliação considera aderência ao pedido, integridade do recorte, cálculo, clareza e utilidade gerencial.

Os números foram comparados com agregações independentes em pandas, sem reutilizar os operadores de cálculo do Terbie. A releitura para validar datas e perfil manteve o mesmo número de registros e total de compras. Todos os registros desta base estão associados a campanhas; isso limita a avaliação de exclusão de compras sem campanha.

**Limite da execução com IA:** foram tentadas 14 chamadas à direção/sugestões do Gemini; apenas 2 retornaram resposta estruturada utilizável, ambas no primeiro cenário. As demais não produziram resposta válida e parte do fluxo usou o planejamento alternativo do próprio Terbie. Esse contador não mede todas as chamadas de raciocínio/narração; não permite concluir a causa da indisponibilidade. A avaliação considera a resposta efetivamente recebida, incluindo o comportamento quando a IA falha.

| Caso | Pergunta | Avaliação | Evidência e observação |
|---|---|---|---|
| D01 | Quais campanhas tiveram o melhor desempenho? | **Não atende** | Promete comparar campanhas, mas responde apenas sobre No Pelo em faturamento e clientes, e dá um total geral de compras. Não entrega ranking nem shopping. A maior soma registrada é Natal 2025 / Buriti Shopping: R$ 22.476.361,12; No Pelo tem R$ 1.856.641,11 e não lidera esse critério. |
| D02 | Mostre o faturamento por campanha, do maior para o menor, identificando o shopping. | **Parcial** | Valores, shopping e ordem por faturamento corretos nas 10 linhas exibidas. Há 38 combinações de campanha e shopping; o sistema aplicou top 10 sem solicitação, embora informe que mostra 10. |
| D03 | Quero comparar clientes únicos por campanha. Identifique o shopping e ordene do maior para o menor. | **Não atende** | Clientes únicos calculados corretamente, mas tabela ordenada por faturamento. Natal / Brasil Park tem 10.005 clientes e deveria preceder Mães e Namorados / Buriti, com 7.800. |
| D04 | Mostre a quantidade de compras por campanha, do maior para o menor, com o shopping. | **Parcial** | Contagem de compras, identificação e ordem corretas, mas repete o corte automático em 10 de 38 campanhas. |
| D05 | Qual o ticket médio por compra por campanha? Mostre também o shopping, do maior para o menor. | **Não atende** | Pedi ticket por compra; recebeu ranking por quantidade de compras. A líder pelo ticket é Mães 2026 / Bay Market, R$ 520,70, e não Natal / Buriti, R$ 364,14. |
| D06 | Compare a campanha de mães 2026 do Buriti Shopping com a campanha de mães 2026 do Shopping Sul. | **Parcial** | Valores das duas campanhas e variações estão corretos: Buriti R$ 10.470.179,98; Sul R$ 1.923.898,90. Identifica os shoppings. Deve avisar que o Buriti tem campanha conjunta Mães e Namorados, enquanto o Sul tem Mães; não é comparação homogênea de eventos/duração. |
| D07 | Qual é o perfil dos participantes das campanhas? | **De acordo** | Conferidos 76.857 clientes, 236.728 compras, ticket R$ 346,08, gênero feminino 67,15%, faixa 35–44 29,57% e Goiânia 24,60%. Explica dados ausentes e que participantes não representam todos os visitantes. |
| D08 | Mostre o faturamento por mês em 2026. Quero entender a evolução ao longo do ano. | **De acordo** | Os sete meses apresentados e respectivos totais batem com o cálculo independente pela data da compra. A ordem é cronológica e o texto avisa que meses sem registros não aparecem. |
| D09 | Qual foi a campanha mais recente e em qual shopping aconteceu? | **Não atende** | Pedi que identificasse o shopping da campanha mais recente. Ele pediu o nome do shopping como se fosse um filtro obrigatório. A base permite responder: Pais 2026 / Shopping Sul, início em 04/08/2026. |
| D10 | Liste as campanhas de 2025 no Buriti Shopping. | **De acordo** | Lista Pais 2025 e Natal 2025 do Buriti Shopping com datas corretas e explica a vigência sobreposta ao ano. |
| D11 | E em 2026? | **Não atende** | A continuação E em 2026? não preserva corretamente a consulta anterior. Retorna erro genérico em vez de listar as campanhas de 2026 do mesmo shopping. |
| D12 | Compare a campanha de pais com a campanha de mães do Buriti Shopping em 2025. | **Não atende** | Não conclui a comparação nem esclarece a ausência de campanha de Mães 2025 do Buriti na base. Deveria informar o que encontrou e qual parte ficou sem dados, preservando o ano solicitado. |
| D13 | Qual campanha teve o maior ROI? Considere o investimento de marketing e o retorno incremental. | **Parcial** | Corretamente não inventa ROI, mas responde apenas que faltam dados. Deveria especificar investimento/custos e retorno incremental, distinguindo valor das compras registradas de retorno atribuível à campanha. |
| D14 | Por que a campanha de Mães 2026 do Shopping Sul vendeu mais? Foi a mídia que causou esse resultado? | **Não atende** | Pedi explicação causal para Mães 2026 / Shopping Sul. Retorna ranking de campanhas de vários shoppings, não responde sobre causalidade e perde o recorte. Deveria dizer que compras registradas, isoladamente, não demonstram efeito da mídia. |
| D15 | Qual foi o faturamento das campanhas do Shopping Inexistente XYZ em 2026? | **Não atende** | Retorna R$ 72.510.620,96 para Shopping Inexistente XYZ. O rastreio mostra filtros de campanha e ano, mas nenhum filtro de shopping. Esse valor é agregado do recorte geral, não do shopping solicitado; deveria pedir esclarecimento ou informar entidade não encontrada. |

## Prioridade de correção

1. **Bloquear respostas com filtros não resolvidos.** Shopping inexistente não pode virar valor da rede. Antes de responder, verificar entidades e recorte solicitado contra o plano realmente executado.
2. **Preservar a métrica principal e sua ordenação.** Clientes, compras e ticket são critérios diferentes. Evitar que palavras como compra dentro de ticket por compra substituam o indicador.
3. **Validar perguntas geradas pela IA.** A promessa de análise por campanha/shopping precisa corresponder aos agrupamentos executados. A primeira pergunta ampla mostrou que as instruções corretas não garantem o cálculo correto.
4. **Manter contexto, ano e referência nas continuações.** Testar variações reais de linguagem, não apenas frases canônicas.
5. **Melhorar a explicação de limites.** Diferenciar campanha inexistente, falta de dados, indisponibilidade técnica e impossibilidade de inferir ROI/causalidade. Informar cortes como top 10 e diferenças de duração entre campanhas.
6. **Investigar disponibilidade do Gemini e monitorar respostas do modo alternativo.** Uma queda de qualidade não pode ficar escondida atrás de respostas aparentemente conclusivas.

## Evidências

- `director-evaluation-2026-09-30.json`: perguntas, respostas integrais, dados agregados, duração, rastreio e parecer por caso.
- `director-evaluation-2026-09-30-oracle.json`: conferência independente do perfil e da série mensal.
- `scripts/evaluate_director.py`: execução reproduzível; com `--deterministic`, não chama o Gemini.
- `scripts/verify_director_data.py`: conferência adicional sem chamar modelos.

A autorização para uso do Gemini foi obtida após bloqueio inicial da revisão automática. Nenhuma publicação no Vercel ou correção de produto foi realizada nesta avaliação.

# Análises de comportamento de compra

O motor reconhece as 20 perguntas e calcula respostas sobre **compras registradas**. Os filtros explícitos de shopping, campanha, segmento e período são preservados. Sem recorte explícito, utiliza o histórico disponível; não herda uma campanha arbitrária da conversa.

| Pergunta | Cálculo implementado |
|---|---|
| 1. Dias da semana | Faturamento e compras únicas por dia da semana, com líderes separados. |
| 2. Frequência | Compras únicas / clientes identificados; por campanha quando a pergunta pede campanha. |
| 3. Concentração dos 10% | Clientes ordenados pelo gasto, grupo com tamanho `ceil(0,10 × N)`, participação no faturamento do recorte. Empates preservam esse tamanho. |
| 4. Evolução do ticket | Ticket por compra calculado diariamente, separado por campanha. Dias sem compra não são preenchidos artificialmente. |
| 5. Faixa etária | Ticket e frequência por faixa; cada indicador pode ter um líder diferente. |
| 6. Homens e mulheres | Comparação por cliente, Welch bilateral, Holm e intervalos individuais. Mínimo operacional de 20 clientes por grupo. |
| 7. Compra única / múltipla | Percentuais de clientes com exatamente uma ou mais compras únicas no recorte. |
| 8. Segmentos e faixa etária | Compras, clientes e faturamento por segmento dentro de cada faixa. |
| 9. Bairros e cidades | Dois níveis de agregação, com UF quando disponível. Os totais entre níveis não devem ser somados. |
| 10. Ticket regional | Por região se houver `regiao`; caso contrário, por município e UF, com interpretação explícita. |
| 11. Clientes de fora | Município e UF comparados com o cadastro do shopping. Denominador: clientes com residência única e suficiente; ausências e conflitos separados. |
| 12. Frequência por bairro | Compras por cliente dentro de UF, município e bairro. |
| 13. Participação dos segmentos | Participação no faturamento e nas compras, com denominadores explícitos. |
| 14. Clientes por loja | Clientes únicos observados em compras por loja e shopping. Isso não demonstra capacidade causal de atração ou fluxo de visitantes. |
| 15. Ticket / recorrência por segmento | Ticket por compra e compras por cliente identificado, com líderes separados. |
| 16. Combinações de segmentos | Pares não ordenados consumidos pelo mesmo cliente; cada cliente conta uma vez por par. Suportes podem se sobrepor. Há limite explícito de trabalho; não se retorna uma amostra silenciosa. |
| 17. Desempenho por campanha | Faturamento, compras e clientes, com identidade da promoção e do shopping preservada. |
| 18. Frequência / gasto por campanha | Frequência média e gasto por cliente dentro de cada campanha. |
| 19. Início, meio e fim | Três intervalos de calendário de duração tão igual quanto possível, usando a vigência declarada. Participação e primeira compra observada na campanha. |
| 20. Múltiplas campanhas | Percentual de clientes presentes em várias campanhas e evolução dos mesmos clientes retornantes contra sua campanha anterior observada. |

## Qualidade e definições

- Uma compra é identificada pelo shopping e `cd_compra`. Duplicatas são removidas. Valores, vínculos ou datas conflitantes na mesma compra são excluídos e informados.
- Os identificadores do shopping e da campanha prevalecem sobre variações dos nomes. IDs ausentes são conciliados pelo nome somente quando existe correspondência única; não se inventa uma entidade.
- Frequência e gasto por cliente usam somente compras com cliente identificado. Faturamento e quantidade de compras gerais também podem incluir compras anônimas válidas; a resposta informa a diferença de população.
- Ticket por compra é faturamento / compras. Gasto por cliente é faturamento dos clientes identificados / clientes identificados.
- Idade é calculada na data da análise, com limite operacional de 0 a 120 anos. Datas inválidas, futuras ou conflitantes por cliente ficam em “Não informado”.
- Clientes podem consumir vários segmentos, bairros e fases. Contagens de clientes desses grupos não são necessariamente aditivas.
- O ranking de lojas não mede atração causal. A base de compras não mede todos os visitantes, conversão de visitantes, lucro, ROI ou efeito causal de marketing.
- Fases exigem início e fim declarados. Evolução entre campanhas exige datas para ordenar os eventos. Campanhas simultâneas não recebem uma ordem artificial.
- A coorte retornante compara os mesmos clientes, mas os gastos e frequências são totais por campanha, sem ajuste por duração ou causalidade.
- Campos necessários ausentes geram uma explicação, sem substituir a análise por outra pergunta. Tabelas longas mostram até 100 grupos, com aviso; as respostas estruturadas mantêm os grupos agregados.

## Cadastro de municípios dos shoppings

O arquivo `app/knowledge/shopping_cities.json` contém o cadastro fornecido pelo usuário em 27/10/2026:

| Shopping | UF | Município |
|---|---|---|
| Buriti Shopping | GO | Aparecida de Goiânia |
| Portal Shopping | GO | Goiânia |
| Águas Lindas Shopping | GO | Águas Lindas de Goiás |
| Brasil Park Shopping | GO | Anápolis |
| Shopping Sul | GO | Valparaíso de Goiás |
| Buriti Shopping Rio Verde | GO | Rio Verde |
| Buriti Shopping Mogi-Guaçu | SP | Mogi-Guaçu |
| Buriti Shopping Guará | SP | Guaratinguetá |

A correspondência normaliza acentos, maiúsculas e separadores. Não infere o município do shopping pela origem predominante dos clientes. Shoppings sem cadastro são apontados explicitamente.

## Atualização do serviço

Instalar as dependências do projeto (incluindo SciPy, utilizado na pergunta 6), atualizar o código e reiniciar o serviço. O cadastro JSON acompanha o pacote. As validações automatizadas não substituem a conferência dos dados na fonte conectada.

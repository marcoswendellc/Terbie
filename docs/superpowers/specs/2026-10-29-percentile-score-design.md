# Score de representatividade e engajamento em compras

Design aprovado na conversa: usar a média dos percentis de faturamento,
quantidade de compras únicas e ticket por compra, com pesos iguais e configuráveis.
Aplicar em perguntas abertas sobre lojas, clientes e bairros; uma métrica explícita
continua prevalecendo. Nenhum limite de resultados é imposto sem pedido.

O recorte autorizado de shopping, campanha e período precede a agregação.
Percentis são calculados sobre todas as entidades elegíveis antes de aplicar top N.
Usar `100 * (rank_average - 1) / (n - 1)`; empates recebem a posição média.
Uma população com apenas uma entidade tem score indefinido, com explicação.
Valores não finitos e entidades sem identificação da dimensão ficam fora do score.
Uma entidade com todos os indicadores empatados recebe score 50 em populações n > 1.

Lojas são distintas por shopping e chave da loja quando disponível; bairros por
UF/cidade/bairro; clientes usam somente compras com identificação e aparecem com
referências anônimas do recorte, sem nomes, contatos ou identificadores brutos.
O score compara compras registradas; não é participação de mercado, probabilidade
ou medida de visitas. Mostrar indicadores originais, percentis, pesos e população.

Alternativas consideradas: manter um único indicador como padrão (insuficiente
para o pedido) ou combinar percentis. A opção aprovada foi combinar três percentis
com pesos iguais. Não há redesenho da interface ou publicação neste trabalho.

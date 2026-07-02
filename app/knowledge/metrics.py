from app.knowledge.models import BusinessMetric

BUSINESS_METRICS: list[BusinessMetric] = [
    BusinessMetric(
        name="faturamento",
        column="vl_compra",
        aggregation="sum",
        synonyms=["vendas", "receita", "valor vendido", "total vendido"],
    ),
    BusinessMetric(
        name="quantidade_compras",
        column="cd_compra",
        aggregation="count_distinct",
        synonyms=["compras", "quantidade de compras", "notas"],
    ),
    BusinessMetric(
        name="clientes_unicos",
        column="sk_cliente",
        aggregation="count_distinct",
        synonyms=["clientes", "compradores", "consumidores únicos"],
    ),
    BusinessMetric(
        name="ticket_medio",
        formula="faturamento / quantidade_compras",
        synonyms=["tm", "valor médio", "média por compra"],
    ),
    BusinessMetric(
        name="frequencia_media",
        formula="quantidade_compras / clientes_unicos",
        synonyms=["frequência", "recorrência média"],
    ),
]

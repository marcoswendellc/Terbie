from app.knowledge.models import BusinessMetric

PROMOTION_COMPARISON_METRICS: list[BusinessMetric] = [
    BusinessMetric(name="faturamento", column="vl_compra", aggregation="sum"),
    BusinessMetric(name="quantidade_compras", column="cd_compra", aggregation="count_distinct"),
    BusinessMetric(name="clientes_unicos", column="sk_cliente", aggregation="count_distinct"),
    BusinessMetric(name="ticket_medio", formula="faturamento / quantidade_compras"),
]

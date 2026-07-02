from app.semantic.models import SemanticMetric
from app.semantic.synonyms import BUSINESS_SYNONYMS

SEMANTIC_METRICS: dict[str, SemanticMetric] = {
    "faturamento": SemanticMetric(
        name="faturamento",
        operation="sum",
        synonyms=BUSINESS_SYNONYMS["faturamento"],
    ),
    "ticket_medio": SemanticMetric(
        name="ticket_medio",
        operation="avg",
        synonyms=BUSINESS_SYNONYMS["ticket_medio"],
    ),
    "quantidade": SemanticMetric(
        name="quantidade",
        operation="count",
        synonyms=["quantidade", "qtd", "total", "contagem", "número", "numero"],
    ),
    "clientes_unicos": SemanticMetric(
        name="clientes_unicos",
        operation="count_distinct",
        synonyms=["clientes únicos", "clientes unicos", "cpfs únicos", "cpfs unicos"],
    ),
    "crescimento": SemanticMetric(
        name="crescimento",
        operation="growth",
        synonyms=BUSINESS_SYNONYMS["crescimento"],
    ),
}

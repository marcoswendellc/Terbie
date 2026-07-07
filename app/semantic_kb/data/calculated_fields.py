from app.semantic_kb.models import KBCalculatedField

KB_CALCULATED_FIELDS: list[KBCalculatedField] = [
    KBCalculatedField(
        name="ticket_medio",
        formula="faturamento / quantidade_compras",
        dependencies=["faturamento", "quantidade_compras"],
        synonyms=["ticket medio", "ticket"],
    ),
    KBCalculatedField(
        name="ticket_medio_por_compra",
        formula="faturamento / quantidade_compras",
        dependencies=["faturamento", "quantidade_compras"],
        synonyms=["ticket medio por compra"],
    ),
    KBCalculatedField(
        name="ticket_medio_por_cliente",
        formula="faturamento / clientes_unicos",
        dependencies=["faturamento", "clientes_unicos"],
        synonyms=["ticket medio por cliente"],
    ),
]


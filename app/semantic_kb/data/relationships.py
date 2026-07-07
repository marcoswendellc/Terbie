from app.semantic_kb.models import KBRelationship

KB_RELATIONSHIPS: list[KBRelationship] = [
    KBRelationship(
        id="promocao_compra",
        source_entity="promocao",
        target_entity="compra",
        fields=["cd_promocao"],
        cardinality="one_to_many",
        description="Uma promocao pode estar associada a varias compras.",
    ),
    KBRelationship(
        id="loja_compra",
        source_entity="loja",
        target_entity="compra",
        fields=["sk_loja"],
        cardinality="one_to_many",
    ),
    KBRelationship(
        id="cliente_compra",
        source_entity="cliente",
        target_entity="compra",
        fields=["sk_cliente"],
        cardinality="one_to_many",
    ),
]


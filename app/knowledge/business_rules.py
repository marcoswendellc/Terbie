from app.knowledge.models import BusinessRule

BUSINESS_RULES: list[BusinessRule] = [
    BusinessRule(
        code="purchase_date",
        description="dt_registro_mos é a data da compra.",
        fields=["dt_registro_mos"],
        concepts=["compra", "tempo"],
    ),
    BusinessRule(
        code="promotion_dates",
        description="sk_dtinicio e sk_dtfim são datas de início e fim da promoção, não da compra.",
        fields=["sk_dtinicio", "sk_dtfim"],
        concepts=["promocao", "tempo"],
    ),
    BusinessRule(
        code="loyalty_purchase",
        description="Se cd_promocao for nulo, a compra deve ser considerada compra de fidelidade.",
        fields=["cd_promocao"],
        concepts=["tipo_compra", "fidelidade"],
    ),
    BusinessRule(
        code="promotional_purchase",
        description="Se cd_promocao não for nulo, a compra pode estar associada a promoção.",
        fields=["cd_promocao"],
        concepts=["tipo_compra", "promocional"],
    ),
    BusinessRule(
        code="loyalty_promotional_purchase",
        description="Uma mesma compra pode estar associada ao fidelidade e à promoção.",
        fields=["cd_compra", "cd_promocao"],
        concepts=["tipo_compra", "fidelidade_promocional"],
    ),
    BusinessRule(
        code="promotion_period_analysis",
        description=(
            "Compras promocionais devem ser analisadas pelo período da promoção "
            "quando a pergunta mencionar promoção/campanha."
        ),
        fields=["sk_dtinicio", "sk_dtfim"],
        concepts=["promocao", "campanha"],
    ),
    BusinessRule(
        code="general_purchase_period_analysis",
        description="Compras gerais devem ser analisadas por dt_registro_mos.",
        fields=["dt_registro_mos"],
        concepts=["compra", "faturamento"],
    ),
    BusinessRule(
        code="purchase_type_classification",
        description=(
            "Classificação conceitual tipo_compra: "
            "fidelidade, promocional, fidelidade_promocional."
        ),
        fields=["cd_promocao"],
        concepts=["tipo_compra", "fidelidade", "promocional", "fidelidade_promocional"],
    ),
]

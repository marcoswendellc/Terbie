from app.semantic_kb.models import KBBusinessRule

KB_BUSINESS_RULES: list[KBBusinessRule] = [
    KBBusinessRule(
        id="campaign_detail_uses_complete_indicator_set",
        description=(
            "Detalhar campanha exige panorama completo com indicadores "
            "e principais recortes."
        ),
        fields=[
            "nm_promocao",
            "vl_compra",
            "cd_compra",
            "sk_cliente",
            "nm_segmento",
            "nm_fantasa",
            "bairro",
            "cidade",
            "nm_empreendimento",
            "sk_dtinicio",
            "sk_dtfim",
        ],
        concepts=["promocao", "campaign_detail"],
        condition={"entity": "promocao", "intent": "campaign_detail"},
        effect={"operation": "campaign_detail"},
        priority=5,
    ),
    KBBusinessRule(
        id="purchase_date",
        description="dt_registro_mos e a data da compra.",
        fields=["dt_registro_mos"],
        concepts=["compra", "tempo"],
    ),
    KBBusinessRule(
        id="promotion_dates",
        description="sk_dtinicio e sk_dtfim são datas de início e fim da promoção.",
        fields=["sk_dtinicio", "sk_dtfim"],
        concepts=["promocao", "tempo"],
    ),
    KBBusinessRule(
        id="promotion_year_uses_period_overlap",
        description="Perguntas de campanha por ano usam sobreposicao entre inicio e fim.",
        fields=["sk_dtinicio", "sk_dtfim"],
        concepts=["promocao", "campanha", "tempo"],
        condition={"entity": "promocao", "filter": "year"},
        effect={"operator": "year_overlap", "field": "sk_dtinicio", "end_field": "sk_dtfim"},
        priority=10,
    ),
    KBBusinessRule(
        id="promotion_rows_require_key",
        description="Compras sem cd_promocao nao devem aparecer como campanhas.",
        fields=["cd_promocao"],
        concepts=["promocao"],
        condition={"entity": "promocao"},
        effect={"operator": "not_null", "field": "cd_promocao"},
        priority=10,
    ),
    KBBusinessRule(
        id="best_campaign_defaults_to_revenue",
        description="Melhor campanha significa maior faturamento, salvo indicador explicito.",
        fields=["vl_compra", "nm_promocao"],
        concepts=["promocao", "ranking", "faturamento"],
        condition={"entity": "promocao", "intent": "ranking", "metric": None},
        effect={"metric": "faturamento", "aggregation": "sum", "limit": 1},
        priority=20,
    ),
    KBBusinessRule(
        id="loyalty_purchase",
        description="Se cd_promocao for nulo, a compra deve ser considerada compra de fidelidade.",
        fields=["cd_promocao"],
        concepts=["tipo_compra", "fidelidade"],
    ),
    KBBusinessRule(
        id="promotional_purchase",
        description="Se cd_promocao nao for nulo, a compra pode estar associada a promocao.",
        fields=["cd_promocao"],
        concepts=["tipo_compra", "promocional"],
    ),
]

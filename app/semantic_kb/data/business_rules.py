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
        concepts=["promocao", "campaign_detail", "campaign_summary"],
        condition={"entity": "promocao", "intent": ["campaign_detail", "campaign_summary"]},
        effect={"operation": "campaign_detail"},
        priority=5,
    ),
    KBBusinessRule(
        id="campaign_detail_rankings_ignore_blank_values",
        description=(
            "Rankings usados no resumo de campanha devem ignorar nulos, vazios e "
            "valores textuais NULL, salvo pedido explicito do usuario."
        ),
        fields=["nm_segmento", "nm_fantasa", "bairro", "cidade"],
        concepts=["promocao", "campaign_detail", "ranking", "not_null"],
        condition={"intent": ["campaign_detail", "campaign_summary"]},
        effect={"ignore_values": [None, "", "NULL", "null", "None", "nan"]},
        priority=6,
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
        id="context_entity_becomes_filter_dimension_question_becomes_grouping",
        description=(
            "Quando uma entidade especifica aparece como contexto e a pergunta pede "
            "outra dimensao, a entidade deve virar filtro e a dimensao perguntada "
            "deve ser usada no agrupamento."
        ),
        fields=[
            "nm_promocao",
            "bairro",
            "cidade",
            "nm_segmento",
            "nm_fantasa",
            "sk_cliente",
        ],
        concepts=["filtro_contextual", "dimensao_perguntada", "ranking"],
        condition={"explicit_entity_context": True, "asked_dimension": True},
        effect={
            "priority": [
                "explicit_filters",
                "asked_dimension",
                "metric",
                "group_by",
                "sort",
                "limit",
            ],
            "never_group_by_filtered_entity": True,
        },
        priority=30,
    ),
    KBBusinessRule(
        id="all_mentioned_entities_are_accumulated_as_filters",
        description=(
            "Toda entidade de negocio mencionada pelo usuario deve ser preservada "
            "como filtro. Identificar uma nova entidade nunca deve remover filtros "
            "ja encontrados."
        ),
        fields=[
            "nm_promocao",
            "nm_fantasa",
            "nm_segmento",
            "bairro",
            "cidade",
            "nm_empreendimento",
        ],
        concepts=["filtros_compostos", "entidades_multiplas"],
        condition={"mentioned_entities_count": {"gte": 2}},
        effect={"accumulate_filters": True, "never_replace_existing_filters": True},
        priority=40,
    ),
    KBBusinessRule(
        id="null_exclusion_terms_filter_asked_dimension",
        description=(
            "Termos como exceto null, ignorando nulos e sem valores vazios "
            "devem remover nulos da dimensao perguntada."
        ),
        fields=["bairro", "cidade", "nm_segmento", "nm_fantasa", "sk_cliente"],
        concepts=["filtro_not_null", "dimensao_perguntada"],
        condition={
            "terms": [
                "exceto null",
                "ignorando nulos",
                "desconsiderando nulos",
                "somente preenchidos",
                "sem valores vazios",
            ],
        },
        effect={"operator": "not_null", "target": "asked_dimension"},
        priority=30,
    ),
    KBBusinessRule(
        id="participation_ranking_defaults_to_purchase_volume",
        description=(
            "Perguntas de maior participacao sem indicador explicito devem usar "
            "quantidade de compras/notas, nao faturamento."
        ),
        fields=["cd_compra"],
        concepts=["ranking", "participacao", "quantidade_compras"],
        condition={"intent": "ranking", "term": "participacao", "metric": None},
        effect={"metric": "quantidade_compras", "aggregation": "count_distinct"},
        priority=30,
    ),
    KBBusinessRule(
        id="registered_notes_are_purchase_volume",
        description="Notas cadastradas representam volume de compras informado.",
        fields=["cd_compra"],
        concepts=["notas", "compras", "quantidade_compras"],
        condition={"terms": ["notas cadastradas", "quantidade de notas", "quantas notas"]},
        effect={"metric": "quantidade_compras", "aggregation": "count_distinct"},
        priority=30,
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

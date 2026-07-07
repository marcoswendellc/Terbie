from app.semantic_kb.models import KBResponseRule

KB_RESPONSE_RULES: list[KBResponseRule] = [
    KBResponseRule(
        id="metric_query_returns_all_requested_metrics",
        intent="metric_query",
        description=(
            "Perguntas com multiplas metricas devem retornar todas as metricas "
            "solicitadas."
        ),
        must_include=["requested_metrics"],
        must_not_include=["single_metric_only"],
        priority=10,
    ),
    KBResponseRule(
        id="campaign_detail_returns_complete_summary",
        intent="campaign_detail",
        entity="promocao",
        description="Detalhes de campanha devem trazer panorama executivo completo.",
        must_include=[
            "faturamento_total",
            "quantidade_compras",
            "ticket_medio_por_cliente",
            "ticket_medio_por_compra",
            "segmento",
            "loja",
            "bairro",
            "cidade",
            "empreendimento",
            "periodo",
        ],
        must_not_include=["single_metric_only", "generic_recommendations_before_summary"],
        suggestions=["Comparar com outra campanha", "Abrir os indicadores por loja"],
        priority=5,
    ),
    KBResponseRule(
        id="listing_returns_items",
        intent="list_distinct",
        description="Listagens devem mostrar os itens encontrados, nao apenas a contagem.",
        must_include=["items"],
        must_not_include=["only_count", "duplicate_highlights"],
        suggestions=[
            "Filtrar por periodo",
            "Comparar itens",
            "Detalhar por categoria",
            "Ver faturamento, quantidade de notas e ticket medio",
        ],
        priority=10,
    ),
    KBResponseRule(
        id="objective_questions_answer_only_requested_result",
        description=(
            "Perguntas objetivas devem responder diretamente ao que foi perguntado, "
            "sem destaques, insights, recomendacoes, comparacoes ou rankings adicionais."
        ),
        must_include=["direct_answer"],
        must_not_include=[
            "automatic_highlights",
            "automatic_insights",
            "generic_recommendations",
            "extra_rankings",
            "unsolicited_comparisons",
        ],
        priority=30,
    ),
    KBResponseRule(
        id="comparison_returns_side_by_side_metrics",
        intent="comparison",
        description="Comparacoes devem trazer itens lado a lado com metricas relevantes.",
        must_include=["compared_items", "metrics"],
    ),
    KBResponseRule(
        id="promotion_summary_uses_main_indicators",
        intent="summary",
        entity="promocao",
        description="Resumo de campanha deve trazer os principais indicadores disponiveis.",
        must_include=[
            "faturamento",
            "quantidade_compras",
            "ticket_medio_por_compra",
            "ticket_medio_por_cliente",
            "lojas",
            "segmentos",
            "bairros",
            "cidades",
            "empreendimento",
        ],
    ),
]

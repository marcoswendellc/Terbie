from app.semantic_kb.models import KBIntent

KB_INTENTS: list[KBIntent] = [
    KBIntent(
        name="metric_query",
        operation="aggregate_metrics",
        synonyms=["qual foi", "quanto foi", "quais foram", "me mostre"],
        response_rule_ids=["metric_query_returns_all_requested_metrics"],
        priority=20,
    ),
    KBIntent(
        name="campaign_detail",
        operation="campaign_detail",
        synonyms=[
            "detalhar campanha",
            "detalhe campanha",
            "resumo campanha",
            "como foi campanha",
            "detalhar promocao",
            "resumo promocao",
        ],
        response_rule_ids=["campaign_detail_returns_complete_summary"],
        priority=5,
    ),
    KBIntent(
        name="campaign_summary",
        operation="campaign_detail",
        synonyms=[
            "resumo executivo campanha",
            "sumario campanha",
            "panorama campanha",
            "analise campanha",
        ],
        response_rule_ids=["campaign_detail_returns_complete_summary"],
        priority=5,
    ),
    KBIntent(
        name="list_distinct",
        operation="distinct",
        synonyms=["quais", "listar", "liste", "mostre", "ocorreram", "existem"],
        response_rule_ids=["listing_returns_items"],
        priority=10,
    ),
    KBIntent(
        name="comparison",
        operation="compare",
        synonyms=["comparar", "comparativo", "versus", "vs", "contra"],
        response_rule_ids=["comparison_returns_side_by_side_metrics"],
    ),
    KBIntent(
        name="summary",
        operation="summary",
        synonyms=["resumo", "resumir", "detalhe", "detalhar", "analise geral", "visao geral"],
        response_rule_ids=["promotion_summary_uses_main_indicators"],
    ),
    KBIntent(
        name="ranking",
        operation="rank",
        synonyms=["ranking", "top", "maior", "maiores", "melhor", "melhores", "mais"],
    ),
]

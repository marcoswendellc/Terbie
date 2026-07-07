from app.semantic_kb.models import KBExample

KB_EXAMPLES: list[KBExample] = [
    KBExample(
        id="campaign_detail_arcaparque_complete_summary",
        question="Pode detalhar a campanha Arcaparque?",
        interpretation={
            "intent": "campaign_detail",
            "entity": "promocao",
            "dimension": "nm_promocao",
            "filter": {"field": "nm_promocao", "value": "Arcaparque"},
            "operation": "campaign_detail",
        },
        expected_response=(
            "Na campanha Arcaparque, o faturamento total foi de R$ X, "
            "com Y compras informadas..."
        ),
        protected=True,
    ),
    KBExample(
        id="campaign_listing_by_year_returns_names",
        question="Quais campanhas ocorreram em 2026?",
        interpretation={
            "intent": "list_distinct",
            "entity": "promocao",
            "dimension": "nm_promocao",
            "filters": {"year": 2026},
            "operation": "distinct",
        },
        expected_response="Em 2026, encontrei as seguintes campanhas: ...",
        protected=True,
    ),
    KBExample(
        id="best_campaign_defaults_to_revenue",
        question="Qual foi a melhor campanha?",
        interpretation={
            "intent": "ranking",
            "entity": "promocao",
            "metric": "faturamento",
            "operation": "rank",
            "limit": 1,
        },
        expected_response="A melhor campanha, considerando faturamento, foi ...",
        protected=True,
    ),
    KBExample(
        id="promotion_summary_main_indicators",
        question="Resumo da campanha Arca Parque.",
        interpretation={
            "intent": "summary",
            "entity": "promocao",
            "dimension": "nm_promocao",
            "metrics": [
                "faturamento",
                "quantidade_compras",
                "ticket_medio_por_compra",
                "ticket_medio_por_cliente",
            ],
            "operation": "summary",
        },
        expected_response="Aqui esta um resumo da campanha com os principais indicadores: ...",
        protected=True,
    ),
]

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
        id="campaign_filter_asked_neighborhood_volume_notes",
        question="Na campanha No Pelo, exceto null, qual foi o bairro de maior participacao em volume de notas?",
        interpretation={
            "intent": "ranking",
            "filters": [
                {"field": "nm_promocao", "value": "No Pelo"},
                {"field": "bairro", "operator": "not_null"},
            ],
            "dimension": "bairro",
            "metric": "quantidade_compras",
            "operation": "rank",
            "sort": {"field": "quantidade_compras", "direction": "desc"},
            "limit": 1,
        },
        expected_response=(
            "O bairro com maior participacao em volume de notas na campanha "
            "No Pelo foi ..., com ... notas cadastradas."
        ),
        protected=True,
    ),
    KBExample(
        id="participation_defaults_to_purchase_volume",
        question="Qual foi a cidade com maior participacao?",
        interpretation={
            "intent": "ranking",
            "dimension": "cidade",
            "metric": "quantidade_compras",
            "operation": "rank",
            "sort": {"field": "quantidade_compras", "direction": "desc"},
            "limit": 1,
        },
        expected_response=(
            "A cidade com maior participacao em volume de notas foi ..., "
            "com ... notas cadastradas."
        ),
        protected=True,
    ),
    KBExample(
        id="objective_ticket_average_answer",
        question="Qual foi o ticket medio?",
        interpretation={
            "intent": "metric_query",
            "metrics": ["ticket_medio_por_compra"],
            "operation": "aggregate",
        },
        expected_response="O ticket medio por compra foi de R$ X.",
        protected=True,
    ),
    KBExample(
        id="objective_purchase_volume_answer",
        question="Quantas notas foram cadastradas?",
        interpretation={
            "intent": "metric_query",
            "metrics": ["quantidade_compras"],
            "operation": "aggregate",
        },
        expected_response="Foram cadastradas X notas.",
        protected=True,
    ),
    KBExample(
        id="store_campaign_revenue_preserves_both_filters",
        question="Qual o faturamento das Casas Bahia na campanha No Pelo?",
        interpretation={
            "intent": "metric_query",
            "metrics": ["faturamento"],
            "filters": [
                {"field": "nm_fantasa", "value": "Casas Bahia"},
                {"field": "nm_promocao", "value": "No Pelo"},
            ],
            "operation": "aggregate",
        },
        expected_response=(
            "O faturamento da loja Casas Bahia na campanha No Pelo foi de R$ X."
        ),
        protected=True,
    ),
    KBExample(
        id="segment_campaign_revenue_preserves_both_filters",
        question="Qual o faturamento do segmento Alimentacao na campanha No Pelo?",
        interpretation={
            "intent": "metric_query",
            "metrics": ["faturamento"],
            "filters": [
                {"field": "nm_segmento", "value": "Alimentacao"},
                {"field": "nm_promocao", "value": "No Pelo"},
            ],
            "operation": "aggregate",
        },
        expected_response=(
            "O faturamento do segmento Alimentacao na campanha No Pelo foi de R$ X."
        ),
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

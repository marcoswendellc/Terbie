from app.knowledge.knowledge_service import KnowledgeService
from app.semantic_kb import get_semantic_kb


def test_semantic_kb_is_canonical_source_for_campaign_memory() -> None:
    kb = get_semantic_kb().knowledge_base

    promotion = next(dimension for dimension in kb.dimensions if dimension.name == "promocao")
    listing_rule = next(rule for rule in kb.response_rules if rule.id == "listing_returns_items")
    example = next(
        example
        for example in kb.examples
        if example.id == "campaign_listing_by_year_returns_names"
    )

    assert promotion.column == "nm_promocao"
    assert "campanhas" in promotion.synonyms
    assert "only_count" in listing_rule.must_not_include
    assert "duplicate_highlights" in listing_rule.must_not_include
    assert example.protected is True
    assert example.interpretation["intent"] == "list_distinct"


def test_knowledge_service_adapts_metrics_dimensions_and_rules_from_semantic_kb() -> None:
    context = KnowledgeService().get_context()

    promotion_dimension = next(
        dimension for dimension in context.dimensions if dimension.name == "promocao"
    )
    revenue_metric = next(metric for metric in context.metrics if metric.name == "faturamento")
    promotion_rule = next(
        rule for rule in context.rules if rule.code == "promotion_rows_require_key"
    )

    assert promotion_dimension.column == "nm_promocao"
    assert promotion_dimension.key == "cd_promocao"
    assert revenue_metric.column == "vl_compra"
    assert revenue_metric.aggregation == "sum"
    assert promotion_rule.fields == ["cd_promocao"]


def test_semantic_kb_projection_keeps_campaign_column_mapping() -> None:
    semantic_dictionary = get_semantic_kb().as_semantic_dictionary()

    assert semantic_dictionary["column_mappings"]["faturamento"] == "vl_compra"
    assert semantic_dictionary["column_mappings"]["quantidade_compras"] == "cd_compra"
    assert semantic_dictionary["column_mappings"]["clientes_unicos"] == "sk_cliente"
    assert semantic_dictionary["column_mappings"]["campanha"] == "nm_promocao"
    assert semantic_dictionary["column_mappings"]["loja"] == "nm_fantasa"
    assert semantic_dictionary["column_mappings"]["empreendimento"] == "nm_empreendimento"
    assert semantic_dictionary["dimensions"]["promocao"]["date_fields"] == [
        "sk_dtinicio",
        "sk_dtfim",
    ]


def test_semantic_kb_registers_campaign_detail_rule() -> None:
    kb = get_semantic_kb().knowledge_base

    intent = next(intent for intent in kb.intents if intent.name == "campaign_detail")
    response_rule = next(
        rule for rule in kb.response_rules if rule.id == "campaign_detail_returns_complete_summary"
    )
    example = next(
        example
        for example in kb.examples
        if example.id == "campaign_detail_arcaparque_complete_summary"
    )

    assert intent.operation == "campaign_detail"
    assert "campaign_detail_returns_complete_summary" in intent.response_rule_ids
    assert "faturamento_total" in response_rule.must_include
    assert "ticket_medio_por_cliente" in response_rule.must_include
    assert "segmento" in response_rule.must_include
    assert "bairro" in response_rule.must_include
    assert "cidade" in response_rule.must_include
    assert "single_metric_only" in response_rule.must_not_include
    assert example.protected is True

from fastapi.testclient import TestClient

from app.knowledge.knowledge_service import KnowledgeService
from app.knowledge.taxonomy import category_for_term, parse_segment
from app.main import app
from app.planner.context_composer import PlannerContextComposer
from app.semantic.resolver import SemanticResolver


def test_knowledge_service_returns_valid_context() -> None:
    context = KnowledgeService().get_context()

    assert context.entities
    assert context.metrics
    assert context.dimensions
    assert context.rules
    assert context.calendars
    assert context.hierarchies
    assert context.taxonomies


def test_faturamento_metric_uses_vl_compra_sum() -> None:
    metric = next(
        metric
        for metric in KnowledgeService().get_metrics()
        if metric.name == "faturamento"
    )

    assert metric.column == "vl_compra"
    assert metric.aggregation == "sum"


def test_ticket_medio_uses_formula() -> None:
    metric = next(
        metric
        for metric in KnowledgeService().get_metrics()
        if metric.name == "ticket_medio"
    )

    assert metric.formula == "faturamento / quantidade_compras"


def test_categoria_dimension_is_derived_from_nm_segmento() -> None:
    dimension = next(
        dimension
        for dimension in KnowledgeService().get_dimensions()
        if dimension.name == "categoria"
    )

    assert dimension.derived_from == "nm_segmento"


def test_purchase_date_rule_uses_dt_registro_mos() -> None:
    rule = next(rule for rule in KnowledgeService().get_rules() if rule.code == "purchase_date")

    assert "dt_registro_mos" in rule.fields
    assert "data da compra" in rule.description


def test_promotion_dates_rule_uses_sk_dtinicio_and_sk_dtfim() -> None:
    rule = next(rule for rule in KnowledgeService().get_rules() if rule.code == "promotion_dates")

    assert rule.fields == ["sk_dtinicio", "sk_dtfim"]
    assert "datas de início e fim da promoção" in rule.description


def test_null_cd_promocao_indicates_loyalty_purchase() -> None:
    rule = next(rule for rule in KnowledgeService().get_rules() if rule.code == "loyalty_purchase")

    assert "cd_promocao" in rule.fields
    assert "fidelidade" in rule.description


def test_segment_taxonomy_parses_category_and_subcategory() -> None:
    parsed = parse_segment("Alimentação >> Restaurante com Serviços")

    assert parsed == {
        "categoria": "Alimentação",
        "subcategoria": "Restaurante com Serviços",
    }
    assert category_for_term("food court") == "Alimentação"


def test_knowledge_context_endpoint_returns_200() -> None:
    client = TestClient(app)

    response = client.get("/knowledge/context")

    assert response.status_code == 200
    assert response.json()["metrics"]


def test_planner_context_composer_accepts_knowledge_context() -> None:
    question = "Quais são os 10 restaurantes com maior faturamento?"
    semantic_resolution = SemanticResolver().resolve(question)
    knowledge_context = KnowledgeService().get_context()

    context = PlannerContextComposer().compose(
        question=question,
        semantic_resolution=semantic_resolution,
        knowledge_context=knowledge_context,
    )

    assert context.knowledge_context == knowledge_context

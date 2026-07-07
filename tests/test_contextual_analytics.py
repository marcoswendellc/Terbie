from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest
from app.context_resolution.context_resolver import ContextResolver
from app.entity_resolution.entity_resolver import EntityResolver
from app.knowledge.knowledge_service import KnowledgeService
from app.metrics.metric_resolver import MetricResolver
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.semantic.resolver import SemanticResolver

ARCA = "Promoção Verão no Arca Parque 2026"
NO_PELO = "No Pelo 360 com Hugo e Guilherme e Buriti Shopping"


def _compile(question: str):
    entity_resolver = EntityResolver()
    metric_resolver = MetricResolver()
    compiler = TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(metric_resolver=metric_resolver),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
        entity_resolver=entity_resolver,
        context_resolver=ContextResolver(
            entity_resolver=entity_resolver,
            metric_resolver=metric_resolver,
        ),
    )
    return compiler.compile(
        CompilerRequest(
            question=question,
            semantic_resolution=SemanticResolver().resolve(question),
            knowledge_context=KnowledgeService().get_context(),
        ),
    )


def _operation(response, operation_type: str, field: str | None = None):
    return next(
        (
            operation
            for operation in response.execution_plan.operations
            if operation.type == operation_type and (field is None or operation.field == field)
        ),
        None,
    )


def test_campaign_context_store_dimension_ranking() -> None:
    response = _compile("Na campanha arcaparque, qual loja mais vendeu?")

    assert response.hypothesis.analysis_type == "ranking"
    assert response.hypothesis.dimensions == ["nm_fantasa"]
    assert response.hypothesis.metric == "faturamento"
    assert _operation(response, "filter", "nm_promocao").parameters["value"] == ARCA
    assert _operation(response, "group_by", "nm_fantasa") is not None
    assert _operation(response, "limit").parameters["value"] == 1


def test_shopping_context_best_campaign_dimension() -> None:
    response = _compile("Para o Buriti Shopping, qual foi a melhor campanha do ano?")

    assert response.hypothesis.analysis_type == "ranking"
    assert response.hypothesis.dimensions == ["nm_promocao"]
    assert response.hypothesis.metric == "faturamento"
    assert (
        _operation(response, "filter", "nm_empreendimento").parameters["value"]
        == "Buriti Shopping"
    )


def test_campaign_summary_context_generates_default_metrics() -> None:
    response = _compile("Me dê um resumo da campanha arcaparque")

    assert response.hypothesis.analysis_type == "campaign_detail"
    assert response.hypothesis.business_entity == "promocao"
    assert _operation(response, "filter", "nm_promocao").parameters["value"] == ARCA
    assert response.analytical_plan.metrics == [
        "faturamento",
        "quantidade_compras",
        "clientes_unicos",
        "ticket_medio_por_compra",
        "ticket_medio_por_cliente",
    ]
    assert _operation(response, "campaign_detail") is not None


def test_neighborhood_ranking_with_campaign_filter() -> None:
    response = _compile("Qual bairro mais comprou na campanha no pelo?")

    assert response.hypothesis.analysis_type == "ranking"
    assert response.hypothesis.dimensions == ["bairro"]
    assert response.hypothesis.metric == "quantidade_compras"
    assert _operation(response, "filter", "nm_promocao").parameters["value"] == NO_PELO
    assert _operation(response, "group_by", "bairro") is not None


def test_context_entity_is_filter_and_asked_dimension_is_grouping() -> None:
    response = _compile(
        "Na campanha No Pelo, exceto null, qual foi o bairro de maior participação "
        "em volume de notas?",
    )

    assert response.hypothesis.analysis_type == "ranking"
    assert response.hypothesis.dimensions == ["bairro"]
    assert response.hypothesis.metric == "quantidade_compras"
    assert _operation(response, "filter", "nm_promocao").parameters["value"] == NO_PELO
    assert _operation(response, "filter", "bairro").parameters["operator"] == "not_null"
    assert _operation(response, "group_by", "bairro") is not None
    assert _operation(response, "group_by", "nm_promocao") is None
    assert _operation(response, "sort", "quantidade_compras").parameters["direction"] == "desc"
    assert _operation(response, "limit").parameters["value"] == 1


def test_segment_ranking_with_shopping_filter() -> None:
    response = _compile("Qual segmento mais vendeu no shopping Buriti?")

    assert response.hypothesis.analysis_type == "ranking"
    assert response.hypothesis.dimensions == ["nm_segmento"]
    assert response.hypothesis.metric == "faturamento"
    assert (
        _operation(response, "filter", "nm_empreendimento").parameters["value"]
        == "Buriti Shopping"
    )


def test_store_ranking_by_customer_ticket_with_campaign_filter() -> None:
    response = _compile("Qual loja teve maior ticket médio por cliente na campanha arcaparque?")

    assert response.hypothesis.analysis_type == "ranking"
    assert response.hypothesis.dimensions == ["nm_fantasa"]
    assert response.hypothesis.metric == "ticket_medio_por_cliente"
    assert _operation(response, "filter", "nm_promocao").parameters["value"] == ARCA

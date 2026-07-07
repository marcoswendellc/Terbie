import pytest

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest
from app.knowledge.knowledge_service import KnowledgeService
from app.metrics.metric_resolver import MetricResolver
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.semantic.resolver import SemanticResolver


def _compile(question: str):
    semantic_resolution = SemanticResolver().resolve(question)
    compiler = TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(metric_resolver=MetricResolver()),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
    )
    return compiler.compile(
        CompilerRequest(
            question=question,
            semantic_resolution=semantic_resolution,
            knowledge_context=KnowledgeService().get_context(),
        ),
    )


@pytest.mark.parametrize(
    ("question", "metric", "source"),
    [
        ("Qual foi a melhor campanha?", "faturamento", "business_default"),
        ("Qual foi a melhor campanha em volume de notas?", "quantidade_compras", "explicit"),
        ("Qual foi a melhor campanha em clientes?", "clientes_unicos", "explicit"),
        ("Qual foi a melhor campanha em ticket médio?", "ticket_medio", "explicit"),
    ],
)
def test_best_campaign_metric_resolution_priority(
    question: str,
    metric: str,
    source: str,
) -> None:
    response = _compile(question)

    assert response.hypothesis.analysis_type == "ranking"
    assert response.hypothesis.business_entity == "promocao"
    assert response.hypothesis.metric == metric
    assert response.hypothesis.metric_source == source


def test_metric_resolver_maps_volume_de_notas_to_quantidade_compras() -> None:
    result = MetricResolver().resolve("Qual foi a melhor campanha em volume de notas?")

    assert result.metric == "quantidade_compras"
    assert result.source == "explicit"
    assert result.matched_term == "volume de notas"

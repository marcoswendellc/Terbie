import pytest

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest
from app.entity_resolution.entity_resolver import EntityResolver
from app.knowledge.knowledge_service import KnowledgeService
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.semantic.resolver import SemanticResolver


@pytest.mark.parametrize(
    ("mention", "field", "value"),
    [
        ("arcaparque", "nm_promocao", "Promoção Verão no Arca Parque 2026"),
        ("camarada", "nm_fantasa", "Camarada Camarão"),
        ("c&a", "nm_fantasa", "C&A"),
        ("boticario", "nm_fantasa", "O Boticário"),
        ("casas bahia", "nm_fantasa", "Casas Bahia"),
    ],
)
def test_entity_resolver_resolves_registered_entities(
    mention: str,
    field: str,
    value: str,
) -> None:
    result = EntityResolver().resolve(f"Qual foi o faturamento de {mention}?")

    assert result.is_ambiguous is False
    assert len(result.matches) == 1
    assert result.matches[0].field == field
    assert result.matches[0].value == value
    assert result.matches[0].confidence >= 0.78


def test_entity_resolution_adds_full_value_filter_to_execution_plan() -> None:
    compiler = TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
        entity_resolver=EntityResolver(),
    )
    question = "Qual foi o faturamento do arcaparque?"
    semantic_resolution = SemanticResolver().resolve(question)

    response = compiler.compile(
        CompilerRequest(
            question=question,
            semantic_resolution=semantic_resolution,
            knowledge_context=KnowledgeService().get_context(),
        ),
    )

    assert response.hypothesis.business_entity == "promocao"
    assert any(
        operation.type == "filter"
        and operation.field == "nm_promocao"
        and operation.parameters["operator"] == "equals"
        and operation.parameters["value"] == "Promoção Verão no Arca Parque 2026"
        for operation in response.execution_plan.operations
    )

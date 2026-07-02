from app.catalog.data_catalog import DataCatalog
from app.planner.compiler import PlannerCompiler
from app.planner.context_composer import PlannerContextComposer
from app.planner.optimizer import PlanOptimizer
from app.planner.parser import PlanParser
from app.planner.validator import PlanValidator
from app.reasoning.mock_provider import MockReasoningProvider
from app.semantic.resolver import SemanticResolver


def _compiler() -> PlannerCompiler:
    return PlannerCompiler(
        context_composer=PlannerContextComposer(),
        reasoning_provider=MockReasoningProvider(),
        parser=PlanParser(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
    )


def test_planner_context_composer_builds_context_with_question_and_semantic_resolution() -> None:
    question = "Quais são os 10 restaurantes com maior faturamento?"
    semantic_resolution = SemanticResolver().resolve(question)

    context = PlannerContextComposer().compose(
        question=question,
        semantic_resolution=semantic_resolution,
        data_catalog=DataCatalog(),
    )

    assert context.question == question
    assert context.semantic_resolution == semantic_resolution
    assert context.data_catalog == {"tables": []}


def test_planner_compiler_returns_valid_planner_response() -> None:
    question = "Quais são os 10 restaurantes com maior faturamento?"
    semantic_resolution = SemanticResolver().resolve(question)

    response = _compiler().compile(
        question=question,
        semantic_resolution=semantic_resolution,
    )

    assert response.question == question
    assert response.plan.intent == "ranking"
    assert any(entity.name == "restaurante" for entity in response.plan.entities)
    assert any(metric.name == "faturamento" for metric in response.plan.metrics)
    assert any(
        parameter.type == "limit" and parameter.value == 10
        for parameter in response.plan.parameters
    )

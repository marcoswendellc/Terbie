from app.reasoning.mock_provider import MockReasoningProvider
from app.reasoning.models import ReasoningContext
from app.semantic.resolver import SemanticResolver


def test_mock_reasoning_provider_returns_valid_reasoning_result() -> None:
    question = "Quais são os 10 restaurantes com maior faturamento?"
    semantic_resolution = SemanticResolver().resolve(question)
    context = ReasoningContext(
        question=question,
        semantic_resolution=semantic_resolution,
    )

    result = MockReasoningProvider().generate_execution_plan(context)

    assert result.execution_plan.version == "1.0"
    assert result.execution_plan.intent == "ranking"
    assert result.messages
    assert result.raw_output is not None

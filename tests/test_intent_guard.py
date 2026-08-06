from typing import Any

import pytest

from app.core.config import Settings
from app.intent_guard import IntentGuard
from app.knowledge.knowledge_service import KnowledgeService
from app.narrator.models import ExecuteResponse
from app.orchestrator.terbie_orchestrator import TerbieOrchestrator
from app.services.execution_service import ExecutionService


class FailingSemanticService:
    def resolve(self, question: str) -> object:
        _ = question
        raise AssertionError("Semantic layer should not be called")


class FailingPlannerService:
    def create_draft_plan(self, **kwargs: Any) -> object:
        _ = kwargs
        raise AssertionError("Compiler/planner should not be called")


class FailingKnowledgeService:
    def get_context(self) -> object:
        raise AssertionError("Knowledge should not be called")


class FailingDataService:
    def read_google_spreadsheet_data(self, **kwargs: Any) -> object:
        _ = kwargs
        raise AssertionError("DataSource should not be called")


class FailingExecutor:
    def execute(self, **kwargs: Any) -> object:
        _ = kwargs
        raise AssertionError("Executor should not be called")


class FailingNarratorService:
    def narrate(self, request: object) -> object:
        _ = request
        raise AssertionError("Narrator should not be called")


@pytest.mark.parametrize(
    ("question", "intent", "requires_data", "should_stop"),
    [
        ("Bom dia, Terbie", "greeting", False, True),
        ("Olá", "greeting", False, True),
        ("Tudo bem?", "greeting", False, True),
        ("Olá Terbie, boa tarde! Tudo bem?", "greeting", False, True),
        ("Saudoso Terbie, tudo bem?", "greeting", False, True),
        ("Saudações, Terbie!", "greeting", False, True),
        ("Obrigado pela ajuda", "greeting", False, True),
        ("O que você consegue fazer?", "capability", False, True),
        ("Quais campanhas existem na base?", "capability", True, False),
        ("Quais campanhas ocorreram em 2026?", "data_query", True, False),
        ("Qual foi o faturamento da Arca Parque?", "data_query", True, False),
        ("Qual foi a melhor?", "clarification", False, True),
        ("Quem descobriu o Brasil?", "out_of_scope", False, True),
    ],
)
def test_intent_router_returns_structured_classification(
    question: str,
    intent: str,
    requires_data: bool,
    should_stop: bool,
) -> None:
    result = IntentGuard().evaluate(question)

    assert result.intent == intent
    assert result.requires_data is requires_data
    assert result.should_stop is should_stop
    assert 0.0 <= result.confidence <= 1.0
    assert result.reason


@pytest.mark.parametrize(
    "question",
    [
        "Bom dia, Terbie",
        "Olá",
        "Tudo bem?",
        "Olá Terbie, boa tarde! Tudo bem?",
        "Saudoso Terbie, tudo bem?",
        "Saudações, Terbie!",
        "Obrigado pela ajuda",
    ],
)
def test_greeting_stops_before_semantic_layer_and_never_returns_out_of_scope(
    question: str,
) -> None:
    service = ExecutionService(
        settings=Settings(
            google_sheets_spreadsheet_id="spreadsheet-id",
            default_table="Dados_copiloto",
        ),
        semantic_service=FailingSemanticService(),
        planner_service=FailingPlannerService(),
        data_service=FailingDataService(),
        executor=FailingExecutor(),
        narrator_service=FailingNarratorService(),
        intent_guard=IntentGuard(),
    )

    response = service.execute_question(
        question=question,
        knowledge_context=KnowledgeService().get_context(),
    )

    assert isinstance(response, ExecuteResponse)
    assert response.data == []
    assert response.metadata == {"data_accessed": False, "response_type": "greeting"}
    assert "fora do meu escopo" not in response.answer.lower()


@pytest.mark.parametrize(
    ("question", "expected_status"),
    [
        ("Bom dia, Terbie", "greeting"),
        ("O que você consegue fazer?", "capability"),
        ("Qual foi a melhor?", "clarification"),
        ("Quem descobriu o Brasil?", "out_of_scope"),
    ],
)
def test_orchestrator_stops_without_query_plan(
    question: str,
    expected_status: str,
) -> None:
    orchestrator = TerbieOrchestrator(
        semantic_service=FailingSemanticService(),
        planner_service=FailingPlannerService(),
        knowledge_service=FailingKnowledgeService(),
        intent_guard=IntentGuard(),
    )

    response = orchestrator.create_draft(question=question)

    assert response.status == expected_status
    assert response.semantic_resolution is None
    assert response.draft_plan is None
    assert response.response


@pytest.mark.parametrize(
    "question",
    [
        "Qual restaurante vendeu mais?",
        "Qual o ticket médio?",
        "Qual campanha teve maior faturamento?",
    ],
)
def test_existing_analytical_questions_continue_to_pipeline(question: str) -> None:
    result = IntentGuard().evaluate(question)

    assert result.intent == "data_query"
    assert result.is_analytical is True


def test_greeting_before_analytical_question_does_not_hide_data_intent() -> None:
    result = IntentGuard().evaluate("Olá Terbie, qual foi o faturamento da campanha?")

    assert result.intent == "data_query"
    assert result.should_stop is False


def test_novel_business_language_reaches_semantic_reasoning() -> None:
    result = IntentGuard().evaluate("Onde estamos deixando dinheiro na mesa?")

    assert result.intent == "data_query"
    assert result.requires_data is True
    assert result.should_stop is False
    assert result.reason == "open_semantic_reasoning_candidate"

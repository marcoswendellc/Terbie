from typing import Any

import pytest

from app.core.config import Settings
from app.intent_guard import IntentGuard
from app.knowledge.knowledge_service import KnowledgeService
from app.narrator.models import ExecuteResponse
from app.orchestrator.terbie_orchestrator import TerbieOrchestrator
from app.services.execution_service import ExecutionService

NON_ANALYTICAL_QUESTIONS = [
    "Olá",
    "Bom dia",
    "Como você trabalha?",
    "Quem é você?",
    "O que você faz?",
    "Conte uma piada",
]

ANALYTICAL_QUESTIONS = [
    "Qual restaurante vendeu mais?",
    "Qual o ticket médio?",
    "Qual campanha teve maior faturamento?",
]


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


@pytest.mark.parametrize("question", NON_ANALYTICAL_QUESTIONS)
def test_intent_guard_blocks_non_analytical_questions(question: str) -> None:
    result = IntentGuard().evaluate(question)

    assert result.is_analytical is False
    assert result.response is not None
    assert "Terbie" in result.response
    assert "Cientista de Dados da Terral" in result.response
    assert "fora do meu escopo" in result.response


@pytest.mark.parametrize("question", ANALYTICAL_QUESTIONS)
def test_intent_guard_allows_analytical_questions(question: str) -> None:
    result = IntentGuard().evaluate(question)

    assert result.is_analytical is True
    assert result.response is None


@pytest.mark.parametrize("question", NON_ANALYTICAL_QUESTIONS)
def test_execution_service_does_not_execute_pipeline_for_non_analytical_questions(
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
    assert response.metadata["data_accessed"] is False
    assert response.metadata["response_type"] == "out_of_scope"
    assert "Cientista de Dados da Terral" in response.answer


@pytest.mark.parametrize("question", NON_ANALYTICAL_QUESTIONS)
def test_orchestrator_does_not_execute_pipeline_for_non_analytical_questions(
    question: str,
) -> None:
    orchestrator = TerbieOrchestrator(
        semantic_service=FailingSemanticService(),
        planner_service=FailingPlannerService(),
        knowledge_service=FailingKnowledgeService(),
        intent_guard=IntentGuard(),
    )

    response = orchestrator.create_draft(question=question)

    assert response.status == "out_of_scope"
    assert response.semantic_resolution is None
    assert response.draft_plan is None
    assert response.response is not None
    assert "Cientista de Dados da Terral" in response.response

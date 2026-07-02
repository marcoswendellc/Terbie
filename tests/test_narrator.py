from fastapi.testclient import TestClient

from app.executor.models import ExecutionResult
from app.main import app
from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.models import NarratorRequest
from app.narrator.narrator import TerbieNarrator


def _narrator() -> TerbieNarrator:
    return TerbieNarrator(
        context_builder=NarrativeContextBuilder(),
        formatter=NarrativeFormatter(),
    )


def test_ranking_execution_result_highlights_first_row() -> None:
    execution_result = ExecutionResult(
        data=[
            {"nm_fantasa": "Restaurante A", "faturamento": 1234567.89},
            {"nm_fantasa": "Restaurante B", "faturamento": 100.0},
        ],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=2,
    )

    response = _narrator().narrate(
        NarratorRequest(
            question="Quais são os restaurantes com maior faturamento?",
            execution_result=execution_result,
        ),
    )

    assert "Restaurante A" in response.answer
    assert "R$ 1.234.567,89" in response.answer
    assert response.highlights == ["Restaurante A, com R$ 1.234.567,89"]


def test_empty_execution_result_returns_safe_answer() -> None:
    execution_result = ExecutionResult(
        data=[],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=0,
    )

    response = _narrator().narrate(
        NarratorRequest(question="Pergunta", execution_result=execution_result),
    )

    assert response.answer == "Não encontrei dados suficientes para responder com segurança."
    assert response.highlights == []


def test_formatter_formats_brazilian_currency() -> None:
    assert NarrativeFormatter().currency_brl(1234567.89) == "R$ 1.234.567,89"


def test_narrator_response_contains_required_fields() -> None:
    execution_result = ExecutionResult(
        data=[{"loja": "A", "faturamento": 300.0}],
        metadata={},
        statistics={},
        warnings=["Aviso teste."],
        execution_time=0.01,
        rows_returned=1,
    )

    response = _narrator().narrate(
        NarratorRequest(question="Pergunta", execution_result=execution_result),
    )

    assert response.answer
    assert response.highlights
    assert response.warnings == ["Aviso teste."]
    assert response.metadata["rows_returned"] == 1


def test_execute_endpoint_returns_200() -> None:
    from app.core.dependencies import provide_execution_service
    from app.narrator.models import ExecuteResponse

    class FakeExecutionService:
        def execute_question(self, *, question: str, knowledge_context):
            _ = question, knowledge_context
            return ExecuteResponse(
                question="Pergunta",
                answer="Resposta determinística.",
                highlights=["Destaque"],
                data=[{"loja": "A"}],
                metadata={},
                warnings=[],
            )

    app.dependency_overrides[provide_execution_service] = lambda: FakeExecutionService()
    try:
        client = TestClient(app)
        response = client.post("/execute", json={"question": "Pergunta"})
    finally:
        app.dependency_overrides.pop(provide_execution_service, None)

    assert response.status_code == 200
    assert response.json()["answer"] == "Resposta determinística."


def test_narrator_draft_endpoint_returns_200() -> None:
    client = TestClient(app)

    response = client.post(
        "/narrator/draft",
        json={
            "question": "Pergunta",
            "execution_result": {
                "data": [{"loja": "A", "faturamento": 300.0}],
                "metadata": {},
                "statistics": {},
                "warnings": [],
                "execution_time": 0.01,
                "rows_returned": 1,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"]

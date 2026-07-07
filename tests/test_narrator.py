from fastapi.testclient import TestClient

from app.executor.models import ExecutionResult
from app.main import app
from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.models import NarratorRequest
from app.narrator.narrator import TerbieNarrator
from app.planner.models import ExecutionPlan


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
    assert not response.answer.startswith("Encontrei")
    assert response.highlights == []


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

    assert response.answer == "Não há dados suficientes para sustentar uma resposta confiável."
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
    assert "Aviso teste." not in response.answer
    assert response.highlights == []
    assert response.warnings == ["Aviso teste."]
    assert response.metadata["technical_warnings"] == ["Aviso teste."]
    assert response.metadata["rows_returned"] == 1


def test_listing_strategy_answers_campaign_question_directly() -> None:
    execution_result = ExecutionResult(
        data=[
            {
                "cd_promocao": "P001",
                "nm_promocao": "Promoção Verão no Arca Parque 2026",
                "sk_dtinicio": 20260114,
                "sk_dtfim": 20260215,
            },
            {
                "cd_promocao": "P002",
                "nm_promocao": "No Pelo 360 com Hugo e Guilherme e Buriti Shopping",
                "sk_dtinicio": 20260319,
                "sk_dtfim": 20260418,
            },
        ],
        metadata={},
        statistics={},
        warnings=["fallback determinístico."],
        execution_time=0.01,
        rows_returned=2,
    )

    response = _narrator().narrate(
        NarratorRequest(
            question="Quais campanhas ocorreram em 2026?",
            execution_result=execution_result,
            execution_plan=ExecutionPlan(intent="list_distinct"),
        ),
    )

    assert response.answer.startswith("Em 2026 ocorreram duas campanhas:")
    assert "Promoção Verão no Arca Parque 2026" in response.answer
    assert "(14/01/2026 a 15/02/2026)" in response.answer
    assert "No Pelo 360 com Hugo e Guilherme e Buriti Shopping" in response.answer
    assert "(19/03/2026 a 18/04/2026)" in response.answer
    assert "Encontrei" not in response.answer
    assert "fallback determinístico" not in response.answer
    assert response.metadata["technical_warnings"] == ["fallback determinístico."]


def test_listing_strategy_uses_friendly_distinct_count() -> None:
    execution_result = ExecutionResult(
        data=[{"categoria": "Alimentacao"}, {"categoria": "Lazer"}],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=2,
    )

    response = _narrator().narrate(
        NarratorRequest(
            question="Quais categorias existem?",
            execution_result=execution_result,
            execution_plan=ExecutionPlan(intent="list_distinct"),
        ),
    )

    assert response.answer.startswith("Encontrei 2 itens distintos na sua consulta:")


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

from fastapi.testclient import TestClient

from app.core.dependencies import provide_planner_service
from app.main import app
from app.semantic.resolver import SemanticResolver


def _create_plan(question: str):
    semantic_resolution = SemanticResolver().resolve(question)
    return provide_planner_service().create_draft_plan(
        question=question,
        semantic_resolution=semantic_resolution,
    )


def test_ranking_restaurantes_faturamento_plan() -> None:
    response = _create_plan("Quais são os 10 restaurantes com maior faturamento?")
    plan = response.plan

    assert plan.intent == "ranking"
    assert any(entity.name == "restaurante" for entity in plan.entities)
    assert any(metric.name == "faturamento" for metric in plan.metrics)
    assert any(parameter.type == "limit" and parameter.value == 10 for parameter in plan.parameters)
    assert any(operation.type == "aggregate" for operation in plan.operations)
    assert any(operation.type == "sort" for operation in plan.operations)
    assert any(operation.type == "limit" for operation in plan.operations)
    assert plan.is_executable is False


def test_ticket_medio_lojas_current_month_plan() -> None:
    response = _create_plan("Qual o ticket médio das lojas este mês?")
    plan = response.plan

    assert any(
        metric.name == "ticket_medio_por_compra"
        for metric in plan.metrics
    )
    assert any(entity.name == "loja" for entity in plan.entities)
    assert any(
        parameter.type == "period" and parameter.value == "current_month"
        for parameter in plan.parameters
    )
    assert plan.is_executable is False


def test_unknown_question_returns_warnings_and_non_executable_plan() -> None:
    response = _create_plan("Como está o clima hoje?")

    assert response.plan.is_executable is False
    assert response.plan.warnings
    assert response.validation.warnings


def test_planner_draft_endpoint_returns_200() -> None:
    client = TestClient(app)

    response = client.post(
        "/planner/draft",
        json={"question": "Quais são os 10 restaurantes com maior faturamento?"},
    )

    assert response.status_code == 200
    assert response.json()["plan"]["intent"] == "ranking"

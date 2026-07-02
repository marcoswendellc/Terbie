from fastapi.testclient import TestClient

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest
from app.knowledge.knowledge_service import KnowledgeService
from app.main import app
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.semantic.resolver import SemanticResolver


def _compiler() -> TerbieCompiler:
    return TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
    )


def _compile(question: str):
    semantic_resolution = SemanticResolver().resolve(question)
    return _compiler().compile(
        CompilerRequest(
            question=question,
            semantic_resolution=semantic_resolution,
            knowledge_context=KnowledgeService().get_context(),
        ),
    )


def test_ranking_restaurante_faturamento_compiler_flow() -> None:
    response = _compile("Quais são os 10 restaurantes com maior faturamento este mês?")

    assert response.hypothesis.analysis_type == "ranking"
    assert response.hypothesis.metric == "faturamento"
    assert response.hypothesis.business_entity == "restaurante"
    assert response.hypothesis.time_scope == "current_month"
    assert set(response.analytical_plan.required_operations) >= {
        "group_by",
        "aggregate",
        "sort",
        "limit",
    }
    assert any(metric.name == "faturamento" for metric in response.execution_plan.metrics)
    assert any(entity.name == "restaurante" for entity in response.execution_plan.entities)


def test_ticket_medio_lojas_current_month_compiler_flow() -> None:
    response = _compile("Qual o ticket médio das lojas este mês?")

    assert response.hypothesis.metric == "ticket_medio"
    assert response.hypothesis.business_entity == "loja"
    assert response.hypothesis.time_scope == "current_month"
    assert any(
        parameter.type == "period" and parameter.value == "current_month"
        for parameter in response.execution_plan.parameters
    )


def test_unknown_question_returns_warnings() -> None:
    response = _compile("Como está o clima hoje?")

    assert response.warnings
    assert response.status in {"draft_created", "completed_with_warnings"}
    assert response.execution_plan.is_executable is False


def test_compiler_draft_endpoint_returns_200() -> None:
    client = TestClient(app)

    response = client.post(
        "/compiler/draft",
        json={"question": "Quais são os 10 restaurantes com maior faturamento este mês?"},
    )

    assert response.status_code == 200
    assert response.json()["hypothesis"]["analysis_type"] == "ranking"


def test_existing_planner_and_ask_draft_endpoints_still_work() -> None:
    client = TestClient(app)
    payload = {"question": "Quais são os 10 restaurantes com maior faturamento este mês?"}

    planner_response = client.post("/planner/draft", json=payload)
    ask_response = client.post("/ask/draft", json=payload)

    assert planner_response.status_code == 200
    assert ask_response.status_code == 200
    assert ask_response.json()["status"] == "draft_created"

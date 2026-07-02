import pandas as pd
from fastapi.testclient import TestClient

from app.core.dependencies import provide_execution_service
from app.executor.engine import PandasExecutionEngine
from app.executor.executor import TerbieExecutor
from app.executor.pipeline import PipelineExecutor
from app.executor.registry import OperationRegistry
from app.knowledge.knowledge_service import KnowledgeService
from app.main import app
from app.narrator.models import ExecuteResponse
from app.planner.models import ExecutionPlan, PlanEntity, PlanMetric, PlanOperation


def _executor() -> TerbieExecutor:
    return TerbieExecutor(
        engine=PandasExecutionEngine(
            pipeline_executor=PipelineExecutor(registry=OperationRegistry()),
        ),
    )


def _dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "nm_fantasa": ["A", "B", "A", "C"],
            "vl_compra": [100.0, 50.0, 200.0, 25.0],
            "cd_compra": ["c1", "c2", "c3", "c4"],
        },
    )


def test_executor_runs_ranking_restaurantes_pipeline() -> None:
    plan = ExecutionPlan(
        intent="ranking",
        entities=[PlanEntity(name="restaurante")],
        metrics=[PlanMetric(name="faturamento", aggregation="sum")],
        operations=[
            PlanOperation(type="group_by", field="loja"),
            PlanOperation(type="aggregate", function="sum", alias="faturamento"),
            PlanOperation(type="sort", field="faturamento", parameters={"direction": "desc"}),
            PlanOperation(type="limit", parameters={"value": 2}),
        ],
    )

    result = _executor().execute(
        dataframe=_dataframe(),
        plan=plan,
        knowledge_context=KnowledgeService().get_context(),
    )

    assert result.rows_returned == 2
    assert result.data[0] == {"nm_fantasa": "A", "faturamento": 300.0}
    assert result.data[1] == {"nm_fantasa": "B", "faturamento": 50.0}
    assert result.metadata["operations"] == ["group_by", "aggregate", "sort", "limit"]


def test_executor_calculates_ticket_medio_by_loja() -> None:
    plan = ExecutionPlan(
        entities=[PlanEntity(name="loja")],
        metrics=[PlanMetric(name="ticket_medio", aggregation="avg")],
        operations=[
            PlanOperation(type="group_by", field="loja"),
            PlanOperation(type="aggregate", function="avg", alias="ticket_medio"),
            PlanOperation(type="sort", field="ticket_medio", parameters={"direction": "desc"}),
        ],
    )

    result = _executor().execute(
        dataframe=_dataframe(),
        plan=plan,
        knowledge_context=KnowledgeService().get_context(),
    )

    rows_by_store = {row["nm_fantasa"]: row["ticket_medio"] for row in result.data}
    assert rows_by_store["A"] == 150.0
    assert rows_by_store["B"] == 50.0
    assert rows_by_store["C"] == 25.0


def test_execute_endpoint_returns_execution_result() -> None:
    class FakeExecutionService:
        def execute_question(self, *, question: str, knowledge_context):
            _ = question, knowledge_context
            return ExecuteResponse(
                question="Quais são os 10 restaurantes com maior faturamento?",
                answer="Encontrei 1 resultado(s). O maior destaque foi A, com R$ 300,00.",
                highlights=["A, com R$ 300,00"],
                data=[{"nm_fantasa": "A", "faturamento": 300.0}],
                metadata={"source": "test"},
                warnings=[],
            )

    app.dependency_overrides[provide_execution_service] = lambda: FakeExecutionService()
    try:
        client = TestClient(app)
        response = client.post(
            "/execute",
            json={"question": "Quais são os 10 restaurantes com maior faturamento?"},
        )
    finally:
        app.dependency_overrides.pop(provide_execution_service, None)

    assert response.status_code == 200
    assert response.json()["answer"]
    assert response.json()["data"][0]["faturamento"] == 300.0

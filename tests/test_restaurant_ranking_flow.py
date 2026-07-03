import pandas as pd
from fastapi.testclient import TestClient

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.core.config import Settings
from app.core.dependencies import provide_execution_service
from app.executor.engine import PandasExecutionEngine
from app.executor.executor import TerbieExecutor
from app.executor.pipeline import PipelineExecutor
from app.executor.registry import OperationRegistry
from app.main import app
from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.narrator import TerbieNarrator
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.semantic.resolver import SemanticResolver
from app.services.execution_service import ExecutionService
from app.services.narrator_service import NarratorService
from app.services.planner_service import PlannerService
from app.services.semantic_service import SemanticService


class RestaurantRankingDataService:
    def read_google_spreadsheet_data(
        self,
        *,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        _ = spreadsheet_id, sheet_names
        rows = [
            {
                "nm_fantasa": f"Restaurante {index:02d}",
                "nm_segmento": "Alimentação >> Restaurante",
                "vl_compra": 1000 - index,
                "cd_compra": f"food-{index}",
            }
            for index in range(12)
        ]
        rows.extend(
            [
                {
                    "nm_fantasa": "Casas Bahia",
                    "nm_segmento": "Departamento",
                    "vl_compra": 9999,
                    "cd_compra": "dept-1",
                },
                {
                    "nm_fantasa": "Magazine Luiza",
                    "nm_segmento": "Eletro",
                    "vl_compra": 9998,
                    "cd_compra": "eletro-1",
                },
                {
                    "nm_fantasa": "Loja de Telefonia",
                    "nm_segmento": "Telefonia",
                    "vl_compra": 9997,
                    "cd_compra": "tel-1",
                },
            ],
        )
        return {"Dados_copiloto": pd.DataFrame(rows)}


def _execution_service() -> ExecutionService:
    compiler = TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
    )
    return ExecutionService(
        settings=Settings(
            google_sheets_spreadsheet_id="spreadsheet-id",
            default_table="Dados_copiloto",
        ),
        semantic_service=SemanticService(resolver=SemanticResolver()),
        planner_service=PlannerService(compiler=compiler),
        data_service=RestaurantRankingDataService(),
        executor=TerbieExecutor(
            engine=PandasExecutionEngine(
                pipeline_executor=PipelineExecutor(registry=OperationRegistry()),
            ),
        ),
        narrator_service=NarratorService(
            narrator=TerbieNarrator(
                context_builder=NarrativeContextBuilder(),
                formatter=NarrativeFormatter(),
            ),
        ),
    )


def test_execute_restaurant_ranking_returns_at_most_10_rows() -> None:
    app.dependency_overrides[provide_execution_service] = _execution_service
    try:
        response = TestClient(app).post(
            "/execute",
            json={"question": "Quais são os 10 restaurantes com maior faturamento?"},
        )
    finally:
        app.dependency_overrides.pop(provide_execution_service, None)

    assert response.status_code == 200
    assert len(response.json()["data"]) <= 10


def test_execute_restaurant_ranking_does_not_return_department_or_phone_stores() -> None:
    app.dependency_overrides[provide_execution_service] = _execution_service
    try:
        response = TestClient(app).post(
            "/execute",
            json={"question": "Quais são os 10 restaurantes com maior faturamento?"},
        )
    finally:
        app.dependency_overrides.pop(provide_execution_service, None)

    store_names = {row["nm_fantasa"] for row in response.json()["data"]}
    assert "Casas Bahia" not in store_names
    assert "Magazine Luiza" not in store_names
    assert "Loja de Telefonia" not in store_names

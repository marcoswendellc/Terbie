import ast
from pathlib import Path

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
from app.knowledge.knowledge_service import KnowledgeService
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


class BestCampaignDataService:
    def __init__(self, *, include_campaigns: bool = True) -> None:
        self._include_campaigns = include_campaigns

    def read_google_spreadsheet_data(
        self,
        *,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        _ = spreadsheet_id, sheet_names
        rows = [
            {
                "cd_promocao": "P001",
                "nm_promocao": "Campanha A",
                "sk_dtinicio": 20260101,
                "sk_dtfim": 20260131,
                "vl_compra": 100.0,
                "cd_compra": "a1",
            },
            {
                "cd_promocao": "P002",
                "nm_promocao": "Campanha B",
                "sk_dtinicio": 20260201,
                "sk_dtfim": 20260228,
                "vl_compra": 300.0,
                "cd_compra": "b1",
            },
            {
                "cd_promocao": None,
                "nm_promocao": "Compra sem campanha",
                "sk_dtinicio": 20260301,
                "sk_dtfim": 20260331,
                "vl_compra": 999.0,
                "cd_compra": "x1",
            },
        ]
        if not self._include_campaigns:
            rows = [rows[-1]]

        return {"Dados_copiloto": pd.DataFrame(rows)}


def _execution_service(*, include_campaigns: bool = True) -> ExecutionService:
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
        data_service=BestCampaignDataService(include_campaigns=include_campaigns),
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


def test_best_campaign_2026_execute_endpoint_does_not_return_500() -> None:
    app.dependency_overrides[provide_execution_service] = _execution_service
    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/execute",
            json={"question": "qual foi a melhor campanha em 2026?"},
        )
    finally:
        app.dependency_overrides.pop(provide_execution_service, None)

    body = response.json()
    assert response.status_code == 200
    assert body["data"][0]["nm_promocao"] == "Campanha B"
    assert body["data"][0]["faturamento"] == 300.0
    assert body["answer"].startswith("A melhor campanha em 2026")
    assert "Warnings" not in body["answer"]


def test_best_campaign_without_year_uses_faturamento_ranking_limit_one() -> None:
    response = _execution_service().execute_question(
        question="melhor campanha",
        knowledge_context=KnowledgeService().get_context(),
    )

    assert len(response.data) == 1
    assert response.data[0]["nm_promocao"] == "Campanha B"
    assert response.metadata["operations"] == [
        "filter",
        "group_by",
        "aggregate",
        "sort",
        "limit",
    ]


def test_best_campaign_when_no_campaign_is_found_returns_safe_answer() -> None:
    response = _execution_service(include_campaigns=False).execute_question(
        question="qual foi a melhor campanha em 2026?",
        knowledge_context=KnowledgeService().get_context(),
    )

    assert response.data == []
    assert "Não há dados suficientes" in response.answer
    assert response.warnings == []


def test_critical_pipeline_has_no_next_without_default() -> None:
    critical_files = [
        Path("app/insights/ranking.py"),
        Path("app/insights/metric.py"),
        Path("app/insights/comparison.py"),
        Path("app/narrator/narrator.py"),
        Path("app/compiler/hypothesis_builder.py"),
        Path("app/compiler/execution_plan_builder.py"),
        Path("app/services/execution_service.py"),
    ]
    offenders: list[str] = []
    for file_path in critical_files:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "next"
                and len(node.args) < 2
            ):
                offenders.append(f"{file_path}:{node.lineno}")

    assert offenders == []

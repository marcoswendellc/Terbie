import pandas as pd
from fastapi.testclient import TestClient

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest
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


NO_PELO = "No Pelo 360 com Hugo e Guilherme e Buriti Shopping"


class CompositeFilterDataService:
    def read_google_spreadsheet_data(
        self,
        *,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        _ = spreadsheet_id, sheet_names
        return {
            "Dados_copiloto": pd.DataFrame(
                [
                    self._row(NO_PELO, "Casas Bahia", "Alimentacao", "Centro", "Goiania", "Buriti Shopping", 100.0),
                    self._row(NO_PELO, "Casas Bahia", "Alimentacao", "Centro", "Goiania", "Buriti Shopping", 200.0),
                    self._row(NO_PELO, "Outra Loja", "Moda", "Sul", "Goiania", "Buriti Shopping", 700.0),
                    self._row("Outra campanha", "Casas Bahia", "Alimentacao", "Centro", "Goiania", "Buriti Shopping", 5000.0),
                    self._row(NO_PELO, "Casas Bahia", "Alimentacao", "Centro", "Goiania", "Outro Shopping", 9000.0),
                ],
            ),
        }

    def _row(
        self,
        campaign: str,
        store: str,
        segment: str,
        neighborhood: str,
        city: str,
        enterprise: str,
        revenue: float,
    ) -> dict[str, object]:
        return {
            "nm_promocao": campaign,
            "cd_promocao": "P1",
            "nm_fantasa": store,
            "nm_segmento": segment,
            "bairro": neighborhood,
            "cidade": city,
            "nm_empreendimento": enterprise,
            "vl_compra": revenue,
            "cd_compra": f"{campaign}-{store}-{enterprise}-{revenue}",
            "sk_cliente": f"c-{revenue}",
            "sk_dtinicio": 20260101,
            "sk_dtfim": 20261231,
        }


def _compiler() -> TerbieCompiler:
    return TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
    )


def _compile(question: str):
    return _compiler().compile(
        CompilerRequest(
            question=question,
            semantic_resolution=SemanticResolver().resolve(question),
            knowledge_context=KnowledgeService().get_context(),
        ),
    )


def _operation(response, operation_type: str, field: str):
    return next(
        (
            operation
            for operation in response.execution_plan.operations
            if operation.type == operation_type and operation.field == field
        ),
        None,
    )


def _execution_service() -> ExecutionService:
    return ExecutionService(
        settings=Settings(
            google_sheets_spreadsheet_id="spreadsheet-id",
            default_table="Dados_copiloto",
        ),
        semantic_service=SemanticService(resolver=SemanticResolver()),
        planner_service=PlannerService(compiler=_compiler()),
        data_service=CompositeFilterDataService(),
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


def _execute(question: str) -> dict[str, object]:
    app.dependency_overrides[provide_execution_service] = _execution_service
    try:
        response = TestClient(app).post("/execute", json={"question": question})
    finally:
        app.dependency_overrides.pop(provide_execution_service, None)

    assert response.status_code == 200
    return response.json()


def _assert_filters(question: str, expected_fields: set[str]) -> None:
    response = _compile(question)
    applied_fields = {
        operation.field
        for operation in response.execution_plan.operations
        if operation.type == "filter"
    }

    assert expected_fields.issubset(applied_fields)


def test_store_and_campaign_filters_are_applied_together() -> None:
    _assert_filters(
        "Qual o faturamento das Casas Bahia na campanha No Pelo?",
        {"nm_fantasa", "nm_promocao"},
    )

    body = _execute("Qual o faturamento das Casas Bahia na campanha No Pelo?")

    assert body["data"] == [{"faturamento": 9300.0}]
    assert body["answer"] == (
        "O faturamento da loja Casas Bahia na campanha No Pelo foi de R$ 9.300,00."
    )
    assert body["highlights"] == []
    assert body["recommendations"] == []


def test_segment_and_campaign_filters_are_applied_together() -> None:
    _assert_filters(
        "Qual o faturamento do segmento Alimentacao na campanha No Pelo?",
        {"nm_segmento", "nm_promocao"},
    )


def test_neighborhood_and_campaign_filters_are_applied_together() -> None:
    _assert_filters(
        "Qual o faturamento do bairro Centro na campanha No Pelo?",
        {"bairro", "nm_promocao"},
    )


def test_city_and_campaign_filters_are_applied_together() -> None:
    _assert_filters(
        "Qual o faturamento da cidade Goiania na campanha No Pelo?",
        {"cidade", "nm_promocao"},
    )


def test_store_enterprise_and_campaign_filters_are_applied_together() -> None:
    _assert_filters(
        "Qual o faturamento das Casas Bahia no Buriti Shopping na campanha No Pelo?",
        {"nm_fantasa", "nm_empreendimento", "nm_promocao"},
    )

    body = _execute("Qual o faturamento das Casas Bahia no Buriti Shopping na campanha No Pelo?")

    assert body["data"] == [{"faturamento": 300.0}]

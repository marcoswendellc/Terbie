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


class PromotionListingDataService:
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
                "nm_promocao": "Volta as aulas",
                "sk_dtinicio": 20260110,
                "sk_dtfim": 20260210,
                "cd_compra": "c1",
                "sk_cliente": "cli-1",
                "vl_compra": 100.0,
                "bairro": "Centro",
                "tx_cep": "74000-000",
            },
            {
                "cd_promocao": "P001",
                "nm_promocao": "Volta as aulas",
                "sk_dtinicio": 20260110,
                "sk_dtfim": 20260210,
                "cd_compra": "c2",
                "sk_cliente": "cli-2",
                "vl_compra": 250.0,
                "bairro": "Centro",
                "tx_cep": "74000-000",
            },
            {
                "cd_promocao": "P002",
                "nm_promocao": "Natal Premiado",
                "sk_dtinicio": 20251215,
                "sk_dtfim": 20260105,
                "cd_compra": "c3",
                "sk_cliente": "cli-3",
                "vl_compra": 300.0,
                "bairro": "Sul",
                "tx_cep": "74100-000",
            },
            {
                "cd_promocao": "P003",
                "nm_promocao": "Campanha 2027",
                "sk_dtinicio": 20270101,
                "sk_dtfim": 20270131,
                "cd_compra": "c4",
                "sk_cliente": "cli-4",
                "vl_compra": 400.0,
                "bairro": "Norte",
                "tx_cep": "74200-000",
            },
            {
                "cd_promocao": None,
                "nm_promocao": "Compra sem campanha",
                "sk_dtinicio": 20260601,
                "sk_dtfim": 20260630,
                "cd_compra": "c5",
                "sk_cliente": "cli-5",
                "vl_compra": 500.0,
                "bairro": "Oeste",
                "tx_cep": "74300-000",
            },
        ]
        return {"Dados_copiloto": pd.DataFrame(rows)}


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


def _execution_service() -> ExecutionService:
    return ExecutionService(
        settings=Settings(
            google_sheets_spreadsheet_id="spreadsheet-id",
            default_table="Dados_copiloto",
        ),
        semantic_service=SemanticService(resolver=SemanticResolver()),
        planner_service=PlannerService(compiler=_compiler()),
        data_service=PromotionListingDataService(),
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


def test_campaign_question_generates_promotion_list_distinct_plan() -> None:
    response = _compile("Quais campanhas ocorreram em 2026?")
    operation_types = [operation.type for operation in response.execution_plan.operations]

    assert response.hypothesis.analysis_type == "list_distinct"
    assert response.hypothesis.business_entity == "promocao"
    assert response.hypothesis.metric is None
    assert response.hypothesis.time_scope == "2026"
    assert any(entity.name == "promocao" for entity in response.execution_plan.entities)
    assert operation_types == ["filter", "filter", "select", "distinct", "sort"]
    assert any(
        operation.type == "filter"
        and operation.field == "sk_dtinicio"
        and operation.parameters == {
            "operator": "year_overlap",
            "value": 2026,
            "end_field": "sk_dtfim",
        }
        for operation in response.execution_plan.operations
    )


def test_promotion_question_generates_same_list_distinct_plan() -> None:
    response = _compile("Quais promoções ocorreram em 2026?")

    assert response.hypothesis.analysis_type == "list_distinct"
    assert response.hypothesis.business_entity == "promocao"
    assert [operation.type for operation in response.execution_plan.operations] == [
        "filter",
        "filter",
        "select",
        "distinct",
        "sort",
    ]


def test_execute_campaign_listing_returns_distinct_promotions_without_raw_purchase_rows() -> None:
    app.dependency_overrides[provide_execution_service] = _execution_service
    try:
        response = TestClient(app).post(
            "/execute",
            json={"question": "Terbie, quais campanhas ocorreram em 2026?"},
        )
    finally:
        app.dependency_overrides.pop(provide_execution_service, None)

    assert response.status_code == 200
    body = response.json()
    rows = body["data"]
    answer = body["answer"]
    assert rows == [
        {
            "cd_promocao": "P002",
            "nm_promocao": "Natal Premiado",
            "sk_dtinicio": 20251215,
            "sk_dtfim": 20260105,
        },
        {
            "cd_promocao": "P001",
            "nm_promocao": "Volta as aulas",
            "sk_dtinicio": 20260110,
            "sk_dtfim": 20260210,
        },
    ]
    assert len({(row["cd_promocao"], row["nm_promocao"]) for row in rows}) == len(rows)
    assert all(row["cd_promocao"] is not None for row in rows)
    assert "Natal Premiado" in answer
    assert "Volta as aulas" in answer
    assert body["highlights"] == []
    assert body["insights"] == []
    assert body["recommendations"] == []
    assert all(
        not {"cd_compra", "sk_cliente", "vl_compra", "bairro", "cep", "tx_cep"}.intersection(row)
        for row in rows
    )


def test_select_and_distinct_keep_only_required_promotion_columns() -> None:
    response = _execution_service().execute_question(
        question="Quais promoções ocorreram em 2026?",
        knowledge_context=KnowledgeService().get_context(),
    )

    assert response.data
    assert all(
        set(row) == {"cd_promocao", "nm_promocao", "sk_dtinicio", "sk_dtfim"}
        for row in response.data
    )
    assert [row["cd_promocao"] for row in response.data] == ["P002", "P001"]

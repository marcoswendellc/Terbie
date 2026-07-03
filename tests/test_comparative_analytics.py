import pandas as pd
from fastapi.testclient import TestClient

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest
from app.core.config import Settings
from app.core.dependencies import provide_execution_service
from app.entity_resolution.entity_resolver import EntityResolver
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

ARCA = "Promoção Verão no Arca Parque 2026"
NO_PELO = "No Pelo 360 com Hugo e Guilherme e Buriti Shopping"


class ComparativeDataService:
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
                    {
                        "cd_promocao": "P001",
                        "nm_promocao": ARCA,
                        "vl_compra": 100.0,
                        "cd_compra": "a1",
                        "sk_cliente": "c1",
                        "bairro": "Centro",
                        "tx_cep": "74000-000",
                    },
                    {
                        "cd_promocao": "P001",
                        "nm_promocao": ARCA,
                        "vl_compra": 300.0,
                        "cd_compra": "a2",
                        "sk_cliente": "c2",
                        "bairro": "Centro",
                        "tx_cep": "74000-000",
                    },
                    {
                        "cd_promocao": "P002",
                        "nm_promocao": NO_PELO,
                        "vl_compra": 500.0,
                        "cd_compra": "n1",
                        "sk_cliente": "c3",
                        "bairro": "Sul",
                        "tx_cep": "74100-000",
                    },
                    {
                        "cd_promocao": "P002",
                        "nm_promocao": NO_PELO,
                        "vl_compra": 700.0,
                        "cd_compra": "n2",
                        "sk_cliente": "c3",
                        "bairro": "Sul",
                        "tx_cep": "74100-000",
                    },
                    {
                        "cd_promocao": "P999",
                        "nm_promocao": "Outra campanha",
                        "vl_compra": 9999.0,
                        "cd_compra": "x1",
                        "sk_cliente": "cx",
                        "bairro": "Oeste",
                        "tx_cep": "74200-000",
                    },
                ],
            ),
        }


def _compiler() -> TerbieCompiler:
    return TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
        entity_resolver=EntityResolver(),
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
        data_service=ComparativeDataService(),
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


def test_comparison_intent_and_multiple_entities_are_detected() -> None:
    response = _compile("compare os indicadores da campanha arcaparque com a no pelo")

    assert response.hypothesis.analysis_type == "comparison"
    assert response.hypothesis.business_entity == "promocao"
    assert [entity["value"] for entity in response.hypothesis.comparison_entities] == [
        ARCA,
        NO_PELO,
    ]


def test_comparison_plan_uses_default_campaign_metrics() -> None:
    response = _compile("compare os indicadores da campanha arcaparque com a no pelo")

    assert response.analytical_plan.intent == "comparison"
    assert response.analytical_plan.entities == ["promocao"]
    assert response.analytical_plan.dimensions == ["nm_promocao"]
    assert response.analytical_plan.metrics == [
        "faturamento",
        "quantidade_compras",
        "clientes_unicos",
        "ticket_medio",
    ]


def test_comparison_execution_plan_contains_filter_group_aggregate_and_derived_metric() -> None:
    response = _compile("compare os indicadores da campanha arcaparque com a no pelo")
    operations = response.execution_plan.operations

    assert any(
        operation.type == "filter"
        and operation.field == "nm_promocao"
        and operation.parameters["operator"] == "in"
        and operation.parameters["value"] == [ARCA, NO_PELO]
        for operation in operations
    )
    assert any(
        operation.type == "group_by" and operation.field == "nm_promocao"
        for operation in operations
    )
    assert any(
        operation.type == "aggregate"
        and [metric["alias"] for metric in operation.parameters["metrics"]]
        == ["faturamento", "quantidade_compras", "clientes_unicos"]
        for operation in operations
    )
    assert any(
        operation.type == "derived_metric" and operation.alias == "ticket_medio"
        for operation in operations
    )


def test_execute_comparison_returns_two_campaign_rows_without_raw_purchase_columns() -> None:
    response = _execution_service().execute_question(
        question="compare os indicadores da campanha arcaparque com a no pelo",
        knowledge_context=KnowledgeService().get_context(),
    )

    assert len(response.data) == 2
    rows_by_campaign = {row["nm_promocao"]: row for row in response.data}
    assert rows_by_campaign[NO_PELO]["faturamento"] == 1200.0
    assert rows_by_campaign[NO_PELO]["quantidade_compras"] == 2
    assert rows_by_campaign[NO_PELO]["clientes_unicos"] == 1
    assert rows_by_campaign[NO_PELO]["ticket_medio"] == 600.0
    assert rows_by_campaign[ARCA]["faturamento"] == 400.0
    assert all(
        not {"cd_compra", "sk_cliente", "bairro", "cep", "tx_cep"}.intersection(row)
        for row in response.data
    )


def test_execute_endpoint_returns_comparative_answer_and_data() -> None:
    app.dependency_overrides[provide_execution_service] = _execution_service
    try:
        response = TestClient(app).post(
            "/execute",
            json={"question": "compare os indicadores da campanha arcaparque com a no pelo"},
        )
    finally:
        app.dependency_overrides.pop(provide_execution_service, None)

    body = response.json()
    assert response.status_code == 200
    assert "Comparando as campanhas" in body["answer"]
    assert "Resumo dos indicadores" in body["answer"]
    assert "Encontrei" not in body["answer"]
    assert len(body["data"]) == 2


def test_single_campaign_question_still_uses_resolved_entity_filter() -> None:
    response = _compile("qual foi o faturamento da campanha no pelo")

    assert response.hypothesis.analysis_type != "comparison"
    assert any(
        operation.type == "filter"
        and operation.field == "nm_promocao"
        and operation.parameters["value"] == NO_PELO
        for operation in response.execution_plan.operations
    )

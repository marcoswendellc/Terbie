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
ARCAPARQUE = "Promo\u00e7\u00e3o Ver\u00e3o no Arca Parque 2026"
BEST_CAMPAIGN = "Campanha B"


class CampaignNeighborhoodDataService:
    def read_google_spreadsheet_data(
        self,
        *,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        _ = spreadsheet_id, sheet_names
        rows: list[dict[str, object]] = [
            self._row(NO_PELO, "P2", "Centro", "Goi\u00e2nia", "Alimenta\u00e7\u00e3o", "Loja A", 100.0, "n1", "c1"),
            self._row(NO_PELO, "P2", "Centro", "Goi\u00e2nia", "Alimenta\u00e7\u00e3o", "Loja A", 200.0, "n2", "c2"),
            self._row(NO_PELO, "P2", "Centro", "Goi\u00e2nia", "Moda", "Loja B", 300.0, "n3", "c1"),
            self._row(NO_PELO, "P2", "Sul", "Aparecida", "Moda", "Loja B", 400.0, "n4", "c3"),
            self._row(NO_PELO, "P2", None, "Goi\u00e2nia", "Moda", "Loja B", 500.0, "n5", "c4"),
            self._row(ARCAPARQUE, "P1", "Centro", "Goi\u00e2nia", "Lazer", "Loja C", 1000.0, "a1", "c5"),
            self._row(ARCAPARQUE, "P1", "Sul", "Goi\u00e2nia", "Lazer", "Loja C", 500.0, "a2", "c6"),
            self._row(BEST_CAMPAIGN, "P3", "Norte", "Bras\u00edlia", "Eletro", "Loja D", 5000.0, "b1", "c7"),
            self._row(BEST_CAMPAIGN, "P3", "Norte", "Bras\u00edlia", "Eletro", "Loja D", 1000.0, "b2", "c8"),
            {
                "nm_promocao": "Outra campanha",
                "cd_promocao": None,
                "bairro": "Centro",
                "cidade": "Goi\u00e2nia",
                "nm_segmento": "Alimenta\u00e7\u00e3o",
                "nm_fantasa": "Loja E",
                "vl_compra": 500.0,
                "cd_compra": "n6",
                "sk_cliente": "c9",
                "nm_empreendimento": "Buriti Shopping",
                "sk_dtinicio": 20260101,
                "sk_dtfim": 20261231,
            },
        ]
        return {"Dados_copiloto": pd.DataFrame(rows)}

    def _row(
        self,
        promotion: str,
        code: str,
        neighborhood: str | None,
        city: str,
        segment: str,
        store: str,
        value: float,
        purchase: str,
        customer: str,
    ) -> dict[str, object]:
        return {
            "nm_promocao": promotion,
            "cd_promocao": code,
            "bairro": neighborhood,
            "cidade": city,
            "nm_segmento": segment,
            "nm_fantasa": store,
            "vl_compra": value,
            "cd_compra": purchase,
            "sk_cliente": customer,
            "nm_empreendimento": "Buriti Shopping",
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


def _operation(response, operation_type: str, field: str | None = None):
    return next(
        (
            operation
            for operation in response.execution_plan.operations
            if operation.type == operation_type and (field is None or operation.field == field)
        ),
        None,
    )


def _execution_service() -> ExecutionService:
    compiler = _compiler()
    return ExecutionService(
        settings=Settings(
            google_sheets_spreadsheet_id="spreadsheet-id",
            default_table="Dados_copiloto",
        ),
        semantic_service=SemanticService(resolver=SemanticResolver()),
        planner_service=PlannerService(compiler=compiler),
        data_service=CampaignNeighborhoodDataService(),
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


def test_campaign_neighborhood_objective_answer_has_no_extra_sections() -> None:
    body = _execute(
        "Na campanha No Pelo, exceto null, qual foi o bairro de maior "
        "participa\u00e7\u00e3o em volume de notas?",
    )

    assert body["answer"] == (
        "O bairro com maior participa\u00e7\u00e3o em volume de notas na campanha "
        "No Pelo foi Centro, com 3 notas cadastradas."
    )
    assert body["highlights"] == []
    assert body["insights"] == []
    assert body["recommendations"] == []
    assert "faturamento" not in body["answer"].lower()
    assert "Ver crescimento" not in body["answer"]


def test_pipeline_interprets_participation_as_purchase_volume() -> None:
    response = _compile("Qual foi o bairro com maior participa\u00e7\u00e3o na campanha No Pelo?")

    assert response.hypothesis.analysis_type == "ranking"
    assert response.hypothesis.metric == "quantidade_compras"
    assert response.hypothesis.dimensions == ["bairro"]
    assert response.hypothesis.warnings == []
    assert _operation(response, "filter", "nm_promocao").parameters["value"] == NO_PELO
    assert _operation(response, "group_by", "bairro") is not None
    assert _operation(response, "group_by", "nm_promocao") is None
    assert _operation(response, "aggregate").field == "cd_compra"
    assert _operation(response, "sort", "quantidade_compras").parameters["direction"] == "desc"
    assert _operation(response, "limit").parameters["value"] == 1


def test_pipeline_metric_questions_are_direct() -> None:
    ticket = _compile("Qual foi o ticket m\u00e9dio?")
    notes = _compile("Quantas notas foram cadastradas?")

    assert ticket.hypothesis.analysis_type == "metric_query"
    assert ticket.analytical_plan.metrics == ["ticket_medio_por_compra"]
    assert _operation(ticket, "select").parameters["fields"] == ["ticket_medio_por_compra"]
    assert notes.hypothesis.analysis_type == "metric_query"
    assert notes.analytical_plan.metrics == ["quantidade_compras"]

    ticket_body = _execute("Qual foi o ticket m\u00e9dio?")
    notes_body = _execute("Quantas notas foram cadastradas?")

    assert ticket_body["answer"] == "O ticket m\u00e9dio por compra foi de R$ 950,00."
    assert notes_body["answer"] == "Foram cadastradas 10 notas."
    assert ticket_body["highlights"] == []
    assert notes_body["recommendations"] == []


def test_pipeline_dimension_rankings_answer_only_requested_result() -> None:
    neighborhood = _execute("Qual foi o bairro com maior participa\u00e7\u00e3o na campanha No Pelo?")
    city = _execute("Qual foi a cidade com maior participa\u00e7\u00e3o?")
    segment = _execute("Qual foi o segmento que mais vendeu?")

    assert neighborhood["answer"] == (
        "O bairro com maior participa\u00e7\u00e3o em volume de notas na campanha "
        "No Pelo foi Centro, com 3 notas cadastradas."
    )
    assert city["answer"] == (
        "A cidade com maior participa\u00e7\u00e3o em volume de notas foi Goi\u00e2nia, "
        "com 7 notas cadastradas."
    )
    assert segment["answer"] == "O segmento com maior faturamento foi Eletro, com R$ 6.000,00."
    assert neighborhood["highlights"] == []
    assert city["insights"] == []
    assert segment["recommendations"] == []


def test_pipeline_expanded_questions_keep_expected_response_shape() -> None:
    summary = _execute("Fa\u00e7a um resumo da campanha Arcaparque.")
    listing = _execute("Quais campanhas ocorreram em 2026?")
    best = _execute("Qual foi a melhor campanha por faturamento?")

    assert "faturamento total" in summary["answer"].lower()
    assert "ticket m\u00e9dio por compra" in summary["answer"].lower()
    assert "bairro" in summary["answer"].lower()
    assert "Em 2026 ocorreram" in listing["answer"]
    assert ARCAPARQUE in listing["answer"]
    assert NO_PELO in listing["answer"]
    assert BEST_CAMPAIGN in listing["answer"]
    assert best["answer"] == f"A melhor campanha, considerando faturamento, foi {BEST_CAMPAIGN}."
    assert best["highlights"] == []

import pandas as pd
import pytest

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.core.config import Settings
from app.executor.engine import PandasExecutionEngine
from app.executor.executor import TerbieExecutor
from app.executor.pipeline import PipelineExecutor
from app.executor.registry import OperationRegistry
from app.knowledge.knowledge_service import KnowledgeService
from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.narrator import TerbieNarrator
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.query_plan.models import MultiQueryPlan, QueryPlan
from app.query_plan.multi import MultiQueryPlanner
from app.semantic.resolver import SemanticResolver
from app.services.execution_service import ExecutionService
from app.services.narrator_service import NarratorService
from app.services.planner_service import PlannerService
from app.services.semantic_service import SemanticService

CAMPAIGN = "Promoção Verão no Arca Parque 2026"
QUESTION = (
    "Quero o top 10 de lojistas do segmento de Calçados por vendas e o ticket "
    "médio geral da campanha Arca Parque."
)


class MultiQueryDataService:
    def read_google_spreadsheet_data(
        self,
        *,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        _ = spreadsheet_id, sheet_names
        rows: list[dict[str, object]] = []
        for index in range(12):
            rows.append(
                {
                    "cd_promocao": "P1",
                    "nm_promocao": CAMPAIGN,
                    "nm_fantasa": f"Calçados {index:02d}",
                    "nm_segmento": "Calçados",
                    "vl_compra": float(100 + index),
                    "cd_compra": f"c-{index}",
                    "sk_cliente": f"client-{index}",
                },
            )
        rows.extend(
            [
                {
                    "cd_promocao": "P1",
                    "nm_promocao": CAMPAIGN,
                    "nm_fantasa": "Moda Geral",
                    "nm_segmento": "Moda",
                    "vl_compra": 1000.0,
                    "cd_compra": "general",
                    "sk_cliente": "general",
                },
                {
                    "cd_promocao": "P2",
                    "nm_promocao": "Outra campanha",
                    "nm_fantasa": "Fora",
                    "nm_segmento": "Calçados",
                    "vl_compra": 9999.0,
                    "cd_compra": "outside",
                    "sk_cliente": "outside",
                },
            ],
        )
        return {"Dados_copiloto": pd.DataFrame(rows)}


class PartiallyFailingExecutor:
    def __init__(self, delegate: TerbieExecutor) -> None:
        self._delegate = delegate

    def execute(self, *, dataframe, plan, knowledge_context):
        if any(metric.name == "ticket_medio_por_compra" for metric in plan.metrics):
            raise RuntimeError("falha simulada no ticket médio")
        return self._delegate.execute(
            dataframe=dataframe,
            plan=plan,
            knowledge_context=knowledge_context,
        )


def _compiler() -> TerbieCompiler:
    return TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
    )


def _planner() -> MultiQueryPlanner:
    return MultiQueryPlanner(
        semantic_service=SemanticService(resolver=SemanticResolver()),
        planner_service=PlannerService(compiler=_compiler()),
    )


def _executor() -> TerbieExecutor:
    return TerbieExecutor(
        engine=PandasExecutionEngine(
            pipeline_executor=PipelineExecutor(registry=OperationRegistry()),
        ),
    )


def _service(*, partial_failure: bool = False) -> ExecutionService:
    executor = _executor()
    return ExecutionService(
        settings=Settings(
            google_sheets_spreadsheet_id="spreadsheet-id",
            default_table="Dados_copiloto",
        ),
        semantic_service=SemanticService(resolver=SemanticResolver()),
        planner_service=PlannerService(compiler=_compiler()),
        data_service=MultiQueryDataService(),
        executor=PartiallyFailingExecutor(executor) if partial_failure else executor,
        narrator_service=NarratorService(
            narrator=TerbieNarrator(
                context_builder=NarrativeContextBuilder(),
                formatter=NarrativeFormatter(),
            ),
        ),
    )


def _multi_plan(question: str = QUESTION) -> MultiQueryPlan:
    plan = _planner().build(
        question=question,
        knowledge_context=KnowledgeService().get_context(),
    )
    assert plan is not None
    return plan


def test_simple_question_keeps_single_plan_compatibility() -> None:
    assert _planner().build(
        question="Qual foi o faturamento da campanha Arca Parque?",
        knowledge_context=KnowledgeService().get_context(),
    ) is None

    response = _service().execute_question(
        question="Qual foi o faturamento da campanha Arca Parque?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.metadata.get("response_type") != "multi_query"


def test_two_indicators_with_same_scope_keep_compatible_single_plan() -> None:
    question = "Quero o faturamento e o ticket médio da campanha Arca Parque."
    assert _planner().build(
        question=question,
        knowledge_context=KnowledgeService().get_context(),
    ) is None

    response = _service().execute_question(
        question=question,
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data[0]["faturamento"] == 2266.0
    assert response.data[0]["ticket_medio_por_compra"] == pytest.approx(2266 / 13)


def test_compound_request_creates_validated_independent_query_plans() -> None:
    plan = _multi_plan()

    assert len(plan.plans) == 2
    assert all(isinstance(item, QueryPlan) for item in plan.plans)
    assert [item.metric for item in plan.plans] == [
        "faturamento",
        "ticket_medio_por_compra",
    ]
    assert [item.id for item in plan.plans] == ["query_1", "query_2"]


def test_ranking_plan_has_multiple_filters_and_requested_top_limit() -> None:
    ranking = _multi_plan().plans[0]

    assert ranking.metric == "faturamento"
    assert ranking.dimensions == ["nm_fantasa"]
    assert ranking.order_by == "faturamento"
    assert ranking.order == "desc"
    assert ranking.top == 10
    assert ranking.limit == 10
    assert {(item["field"], item["value"]) for item in ranking.filters} == {
        ("nm_promocao", CAMPAIGN),
        ("nm_segmento", "Calçados"),
    }


def test_general_metric_does_not_inherit_segment_filter() -> None:
    ranking, general_metric = _multi_plan().plans

    assert any(item["field"] == "nm_segmento" for item in ranking.filters)
    assert general_metric.metric == "ticket_medio_por_compra"
    assert general_metric.dimensions == []
    assert general_metric.filters == [
        {"field": "nm_promocao", "operator": "equals", "value": CAMPAIGN},
    ]


@pytest.mark.parametrize(
    "scope",
    ["geral", "total", "independentemente do segmento"],
)
def test_independent_scope_expressions_do_not_propagate_segment(scope: str) -> None:
    question = (
        "Quero o top 10 de lojistas do segmento de Calçados por vendas e o "
        f"ticket médio {scope} da campanha Arca Parque."
    )
    _, general_metric = _multi_plan(question).plans

    assert general_metric.dimensions == []
    assert not any(item["field"] == "nm_segmento" for item in general_metric.filters)


def test_combined_ranking_and_general_indicator_are_consolidated() -> None:
    response = _service().execute_question(
        question=QUESTION,
        knowledge_context=KnowledgeService().get_context(),
    )

    assert response.metadata["response_type"] == "multi_query"
    assert response.metadata["successful_plans"] == 2
    assert len(response.data) == 2
    ranking, ticket = response.data
    assert ranking["id"] == "query_1"
    assert ranking["title"] == "Ranking de lojas por faturamento"
    assert len(ranking["data"]) == 10
    assert ranking["data"][0]["nm_fantasa"] == "Calçados 11"
    assert ticket["id"] == "query_2"
    assert ticket["title"] == "Ticket médio por compra"
    assert ticket["data"][0]["ticket_medio_por_compra"] == pytest.approx(2266 / 13)
    assert "segmento = Calçados" in response.answer
    assert "Ticket médio por compra" in response.answer


def test_partial_failure_preserves_successful_plan_result() -> None:
    response = _service(partial_failure=True).execute_question(
        question=QUESTION,
        knowledge_context=KnowledgeService().get_context(),
    )

    assert response.metadata["successful_plans"] == 1
    assert response.metadata["failed_plans"] == 1
    assert response.data[0]["status"] == "success"
    assert response.data[0]["data"]
    assert response.data[1]["status"] == "failed"
    assert "não foi possível responder esta parte" in response.answer


def test_campaign_is_filter_and_never_ranking_dimension() -> None:
    ranking = _multi_plan().plans[0]

    assert ranking.dimensions == ["nm_fantasa"]
    assert "nm_promocao" not in ranking.dimensions
    assert any(item["field"] == "nm_promocao" for item in ranking.filters)

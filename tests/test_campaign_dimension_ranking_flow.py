import pandas as pd
import pytest

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest
from app.core.config import Settings
from app.executor.engine import PandasExecutionEngine
from app.executor.executor import TerbieExecutor
from app.executor.pipeline import PipelineExecutor
from app.executor.registry import OperationRegistry
from app.intent_guard import IntentGuard
from app.knowledge.knowledge_service import KnowledgeService
from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.narrator import TerbieNarrator
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.query_plan.builder import LogicalQueryPlanBuilder
from app.semantic.resolver import SemanticResolver
from app.services.execution_service import ExecutionService
from app.services.narrator_service import NarratorService
from app.services.planner_service import PlannerService
from app.services.semantic_service import SemanticService

QUESTION = "Me liste o top 10 de lojas por faturamento da campanha Arca Parque"
EXACT_QUESTION = "Liste as 10 lojas que mais venderam na campanha Arca Parque"
PURCHASE_RANKING_QUESTION = (
    "Gostaria do ranking 10 de lojas por quantidade de compras na campanha Arca Parque?"
)
CAMPAIGN = "Promoção Verão no Arca Parque 2026"


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
    response = _compiler().compile(
        CompilerRequest(
            question=question,
            semantic_resolution=semantic_resolution,
            knowledge_context=KnowledgeService().get_context(),
        ),
    )
    return semantic_resolution, response


class CampaignRankingDataService:
    def read_google_spreadsheet_data(
        self,
        *,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        _ = spreadsheet_id, sheet_names
        rows: list[dict[str, object]] = []
        for index in range(12):
            store = f"Loja {chr(65 + index)}"
            for purchase in range(index + 1):
                rows.append(
                    {
                        "cd_promocao": "P001",
                        "nm_promocao": CAMPAIGN,
                        "nm_fantasa": store,
                        "nm_segmento": "Moda" if index % 2 == 0 else "Alimentação",
                        "bairro": "Centro" if index < 7 else "Sul",
                        "vl_compra": float((index + 1) * 100),
                        "cd_compra": f"{index}-{purchase}",
                        "sk_cliente": f"cliente-{index}-{purchase % 3}",
                    },
                )
        rows.append(
            {
                "cd_promocao": "P999",
                "nm_promocao": "Outra campanha",
                "nm_fantasa": "Loja Fora do Filtro",
                "nm_segmento": "Moda",
                "bairro": "Norte",
                "vl_compra": 999999.0,
                "cd_compra": "outside",
                "sk_cliente": "outside",
            },
        )
        return {"Dados_copiloto": pd.DataFrame(rows)}


def _execution_service() -> ExecutionService:
    return ExecutionService(
        settings=Settings(
            google_sheets_spreadsheet_id="spreadsheet-id",
            default_table="Dados_copiloto",
        ),
        semantic_service=SemanticService(resolver=SemanticResolver()),
        planner_service=PlannerService(compiler=_compiler()),
        data_service=CampaignRankingDataService(),
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


def test_original_question_produces_store_ranking_query_plan() -> None:
    router_result = IntentGuard().evaluate(QUESTION)
    semantic_resolution, response = _compile(QUESTION)
    plan = response.execution_plan
    logical_plan = LogicalQueryPlanBuilder().build(plan)

    assert router_result.intent == "data_query"
    assert semantic_resolution.interpretation is not None
    assert semantic_resolution.interpretation.intent == "ranking"
    assert plan.intent == "ranking"
    assert plan.metrics[0].name == "faturamento"
    assert plan.metrics[0].aggregation == "sum"
    assert any(
        operation.type == "filter"
        and operation.field == "nm_promocao"
        and operation.parameters["value"] == CAMPAIGN
        for operation in plan.operations
    )
    assert any(
        operation.type == "group_by" and operation.field == "nm_fantasa"
        for operation in plan.operations
    )
    assert any(
        operation.type == "sort"
        and operation.field == "faturamento"
        and operation.parameters["direction"] == "desc"
        for operation in plan.operations
    )
    assert any(
        operation.type == "limit" and operation.parameters["value"] == 10
        for operation in plan.operations
    )
    assert [node.type for node in logical_plan.nodes][-4:] == [
        "group_by",
        "aggregate",
        "sort",
        "limit",
    ]


def test_original_question_executes_store_ranking_and_lists_only_query_results() -> None:
    response = _execution_service().execute_question(
        question=QUESTION,
        knowledge_context=KnowledgeService().get_context(),
    )

    assert len(response.data) == 10
    assert response.data[0] == {"nm_fantasa": "Loja L", "faturamento": 14400.0}
    assert all(row["nm_fantasa"] != "Loja Fora do Filtro" for row in response.data)
    assert response.answer.startswith(
        "As 10 lojas com maior faturamento na campanha Arca Parque foram:",
    )
    assert "1. Loja L — R$ 14.400,00" in response.answer
    assert "10. Loja C — R$ 900,00" in response.answer


def test_exact_store_sales_question_uses_campaign_only_as_filter() -> None:
    semantic_resolution, response = _compile(EXACT_QUESTION)
    plan = response.execution_plan

    assert semantic_resolution.interpretation is not None
    assert semantic_resolution.interpretation.intent == "ranking"
    assert semantic_resolution.interpretation.entity == "loja"
    assert semantic_resolution.interpretation.dimensions == ["nm_fantasa"]
    assert response.hypothesis.metric == "faturamento"
    assert response.hypothesis.dimensions == ["nm_fantasa"]
    assert any(
        item.get("type") == "limit" and item.get("value") == 10
        for item in response.hypothesis.filters
    )
    assert any(
        parameter.type == "limit" and parameter.value == 10
        for parameter in plan.parameters
    )
    assert any(
        operation.type == "filter" and operation.field == "nm_promocao"
        for operation in plan.operations
    )
    assert any(
        operation.type == "group_by" and operation.field == "nm_fantasa"
        for operation in plan.operations
    )
    assert not any(
        operation.type == "group_by" and operation.field == "nm_promocao"
        for operation in plan.operations
    )
    assert any(
        operation.type == "sort"
        and operation.field == "faturamento"
        and operation.parameters["direction"] == "desc"
        for operation in plan.operations
    )
    assert any(
        operation.type == "limit" and operation.parameters["value"] == 10
        for operation in plan.operations
    )


def test_exact_store_sales_question_executes_ten_filtered_rows() -> None:
    response = _execution_service().execute_question(
        question=EXACT_QUESTION,
        knowledge_context=KnowledgeService().get_context(),
    )

    assert len(response.data) == 10
    assert list(response.data[0]) == ["nm_fantasa", "faturamento"]
    assert response.data[0] == {"nm_fantasa": "Loja L", "faturamento": 14400.0}
    assert all(row["nm_fantasa"] != "Loja Fora do Filtro" for row in response.data)


def test_store_ranking_volume_phrases_use_purchase_count() -> None:
    for phrase in ("quantidade de compras", "volume de notas"):
        _, response = _compile(
            f"Liste as 10 lojas por {phrase} na campanha Arca Parque",
        )
        plan = response.execution_plan

        assert plan.metrics[0].name == "quantidade_compras"
        assert any(
            operation.type == "group_by" and operation.field == "nm_fantasa"
            for operation in plan.operations
        )
        assert not any(
            operation.type == "group_by" and operation.field == "nm_promocao"
            for operation in plan.operations
        )
        assert any(
            operation.type == "aggregate"
            and operation.field == "cd_compra"
            and operation.function == "count_distinct"
            for operation in plan.operations
        )
        assert any(
            operation.type == "limit" and operation.parameters["value"] == 10
            for operation in plan.operations
        )


def test_ranking_10_inside_campaign_preserves_limit_through_execution() -> None:
    semantic_resolution, compiler_response = _compile(PURCHASE_RANKING_QUESTION)
    plan = compiler_response.execution_plan
    response = _execution_service().execute_question(
        question=PURCHASE_RANKING_QUESTION,
        knowledge_context=KnowledgeService().get_context(),
    )

    assert any(
        parameter.type == "limit" and parameter.value == 10
        for parameter in semantic_resolution.parameters
    )
    assert any(
        operation.type == "limit" and operation.parameters["value"] == 10
        for operation in plan.operations
    )
    assert len(response.data) == 10
    assert response.metadata["ranking"] == {
        "requested_limit": 10,
        "planned_limit": 10,
        "executed_limit": 10,
        "order": "desc",
        "order_by": "quantidade_compras",
    }
    assert response.answer.count("\n") >= 10
    assert "1. Loja L — 12" in response.answer
    assert "10. Loja C — 3" in response.answer


def test_campaign_summary_remains_campaign_detail() -> None:
    _, response = _compile("Resuma a campanha Arca Parque")

    assert response.execution_plan.intent == "campaign_detail"
    assert any(
        operation.type == "campaign_detail"
        for operation in response.execution_plan.operations
    )


def test_campaign_rankings_preserve_requested_dimension_and_metric() -> None:
    cases = [
        (
            "Quais segmentos mais faturaram na Arca Parque?",
            "nm_segmento",
            "faturamento",
        ),
        (
            "Qual bairro teve mais clientes na Arca Parque?",
            "bairro",
            "clientes_unicos",
        ),
        (
            "Top 5 lojas por quantidade de notas na Arca Parque",
            "nm_fantasa",
            "quantidade_compras",
        ),
    ]

    for question, expected_dimension, expected_metric in cases:
        _, response = _compile(question)
        plan = response.execution_plan

        assert plan.intent == "ranking"
        assert plan.metrics[0].name == expected_metric
        assert any(
            operation.type == "group_by" and operation.field == expected_dimension
            for operation in plan.operations
        )
        assert not any(
            operation.type == "campaign_detail"
            for operation in plan.operations
        )

    top_five_plan = _compile(cases[-1][0])[1].execution_plan
    assert any(
        operation.type == "limit" and operation.parameters["value"] == 5
        for operation in top_five_plan.operations
    )


def test_explicit_and_default_ranking_limits() -> None:
    cases = [
        ("ranking 5 de lojas por faturamento", 5),
        ("top 3 lojas por faturamento", 3),
        ("as 20 lojas com mais compras", 20),
        ("dez lojas com mais compras", 10),
        ("liste as 10 maiores lojas", 10),
        ("qual loja mais vendeu", 1),
        ("lojas que mais venderam", 10),
    ]

    for question, expected_limit in cases:
        semantic_resolution, response = _compile(question)
        limit_operation = next(
            operation
            for operation in response.execution_plan.operations
            if operation.type == "limit"
        )

        assert limit_operation.parameters["value"] == expected_limit
        if any(char.isdigit() for char in question) or question.startswith("dez"):
            assert any(
                parameter.type == "limit" and parameter.value == expected_limit
                for parameter in semantic_resolution.parameters
            )

    _, singular_campaign = _compile(
        "qual a campanha promocional teve melhor resultado em 2026"
    )
    singular_limit = next(
        operation
        for operation in singular_campaign.execution_plan.operations
        if operation.type == "limit"
    )
    assert singular_limit.parameters["value"] == 1


@pytest.mark.parametrize(
    ("question", "dimension", "metric", "limit"),
    [
        (
            "Quais foram as 10 lojas que mais tiveram notas inseridas "
            "na campanha Arca Parque?",
            "nm_fantasa",
            "quantidade_compras",
            10,
        ),
        (
            "5 lojas com mais compras na campanha Arca Parque",
            "nm_fantasa",
            "quantidade_compras",
            5,
        ),
        (
            "segmentos com mais notas na campanha Arca Parque",
            "nm_segmento",
            "quantidade_compras",
            10,
        ),
        (
            "campanhas com mais notas em 2026",
            "nm_promocao",
            "quantidade_compras",
            10,
        ),
        (
            "lojas que mais venderam na campanha Arca Parque",
            "nm_fantasa",
            "faturamento",
            10,
        ),
        (
            "campanha com mais notas em 2026",
            "nm_promocao",
            "quantidade_compras",
            10,
        ),
    ],
)
def test_requested_ranking_object_has_priority_over_context_filter(
    question: str,
    dimension: str,
    metric: str,
    limit: int,
) -> None:
    semantic_resolution, response = _compile(question)
    plan = response.execution_plan

    assert semantic_resolution.interpretation is not None
    assert semantic_resolution.interpretation.intent == "ranking"
    assert plan.metrics[0].name == metric
    assert any(
        operation.type == "group_by" and operation.field == dimension
        for operation in plan.operations
    )
    assert any(
        operation.type == "sort"
        and operation.field == metric
        and operation.parameters["direction"] == "desc"
        for operation in plan.operations
    )
    assert any(
        operation.type == "limit" and operation.parameters["value"] == limit
        for operation in plan.operations
    )
    if "Arca Parque" in question:
        assert any(
            operation.type == "filter"
            and operation.field == "nm_promocao"
            and operation.parameters["value"] == CAMPAIGN
            for operation in plan.operations
        )
        if dimension != "nm_promocao":
            assert not any(
                operation.type == "group_by" and operation.field == "nm_promocao"
                for operation in plan.operations
            )
        if metric == "quantidade_compras":
            assert plan.metrics[0].aggregation == "count_distinct"
            assert any(
                operation.type == "aggregate"
                and (
                    (
                        operation.field == "cd_compra"
                        and operation.function == "count_distinct"
                    )
                    or any(
                        item.get("field") == "cd_compra"
                        and item.get("function") == "count_distinct"
                        for item in operation.parameters.get("metrics", [])
                    )
                )
                for operation in plan.operations
            )


def test_store_notes_ranking_executes_and_reuses_full_ranking_formatter() -> None:
    question = (
        "Quais foram as 10 lojas que mais tiveram notas inseridas "
        "na campanha Arca Parque?"
    )
    response = _execution_service().execute_question(
        question=question,
        knowledge_context=KnowledgeService().get_context(),
    )

    assert len(response.data) == 10
    assert list(response.data[0]) == ["nm_fantasa", "quantidade_compras"]
    assert response.data[0] == {"nm_fantasa": "Loja L", "quantidade_compras": 12}
    assert response.answer.startswith(
        "As 10 lojas com maior participação em volume de notas "
        "na campanha Arca Parque foram:",
    )
    assert "1. Loja L — 12" in response.answer
    assert "10. Loja C — 3" in response.answer
def test_multi_metric_store_top_ten_defaults_to_revenue_and_calculates_ticket() -> None:
    question = (
        "Monte uma tabela com dados de ticket médio, faturamento, quantidade de notas "
        "com o top 10 de lojas da campanha de mães do Shopping Sul"
    )

    _, response = _compile(question)
    plan = response.execution_plan

    assert [metric.name for metric in plan.metrics] == [
        "faturamento",
        "ticket_medio_por_compra",
        "quantidade_compras",
    ]
    assert any(operation.type == "derived_metric" for operation in plan.operations)
    assert any(
        operation.type == "sort"
        and operation.field == "faturamento"
        and operation.parameters["direction"] == "desc"
        for operation in plan.operations
    )
    assert plan.operations[-1].type == "limit"
    assert plan.operations[-1].parameters["value"] == 10

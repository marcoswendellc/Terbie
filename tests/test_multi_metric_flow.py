import pandas as pd

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
from app.semantic.resolver import SemanticResolver
from app.services.execution_service import ExecutionService
from app.services.narrator_service import NarratorService
from app.services.planner_service import PlannerService
from app.services.semantic_service import SemanticService


class MultiMetricDataService:
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
                    {"vl_compra": 100.0, "cd_compra": "n1", "sk_cliente": "c1"},
                    {"vl_compra": 50.0, "cd_compra": "n2", "sk_cliente": "c1"},
                    {"vl_compra": 150.0, "cd_compra": "n3", "sk_cliente": "c2"},
                ],
            ),
        }


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
        data_service=MultiMetricDataService(),
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


def test_two_metrics_are_interpreted_and_calculated() -> None:
    resolution = SemanticResolver().resolve(
        "Qual foi o ticket médio e o volume de notas cadastradas?",
    )

    assert resolution.interpretation is not None
    assert resolution.interpretation.intent == "metric_query"
    assert resolution.interpretation.metrics == [
        "ticket_medio_por_compra",
        "quantidade_compras",
    ]

    response = _execution_service().execute_question(
        question="Qual foi o ticket médio e o volume de notas cadastradas?",
        knowledge_context=KnowledgeService().get_context(),
    )

    assert response.data == [{"ticket_medio_por_compra": 100.0, "quantidade_compras": 3}]
    assert "ticket médio por compra" in response.answer.lower()
    assert "volume de notas cadastradas" in response.answer.lower()
    assert "indicador quantidade compras foi calculado" not in response.answer.lower()


def test_three_metrics_are_interpreted_and_calculated() -> None:
    response = _execution_service().execute_question(
        question="Qual foi o faturamento, ticket médio e clientes únicos?",
        knowledge_context=KnowledgeService().get_context(),
    )

    assert response.data == [
        {
            "faturamento": 300.0,
            "ticket_medio_por_compra": 100.0,
            "clientes_unicos": 2,
        },
    ]
    assert "faturamento" in response.answer.lower()
    assert "ticket médio por compra" in response.answer.lower()
    assert "clientes únicos" in response.answer.lower()


def test_four_metrics_are_interpreted_and_calculated() -> None:
    response = _execution_service().execute_question(
        question=(
            "Qual foi o faturamento, ticket médio, clientes únicos e quantidade de notas?"
        ),
        knowledge_context=KnowledgeService().get_context(),
    )

    assert response.data == [
        {
            "faturamento": 300.0,
            "ticket_medio_por_compra": 100.0,
            "clientes_unicos": 2,
            "quantidade_compras": 3,
        },
    ]
    assert "faturamento" in response.answer.lower()
    assert "ticket médio por compra" in response.answer.lower()
    assert "clientes únicos" in response.answer.lower()
    assert "volume de notas cadastradas" in response.answer.lower()


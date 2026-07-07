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


class CampaignDetailDataService:
    def __init__(self, *, drop_columns: list[str] | None = None) -> None:
        self._drop_columns = drop_columns or []

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
                "nm_promocao": "Promoção Verão no Arca Parque 2026",
                "sk_dtinicio": 20260101,
                "sk_dtfim": 20260131,
                "cd_compra": "c1",
                "sk_cliente": "cli-1",
                "vl_compra": 100.0,
                "nm_segmento": "Alimentação",
                "nm_fantasa": "Restaurante A",
                "bairro": "Centro",
                "cidade": "Goiânia",
                "nm_empreendimento": "Arca Parque",
            },
            {
                "cd_promocao": "P001",
                "nm_promocao": "Promoção Verão no Arca Parque 2026",
                "sk_dtinicio": 20260101,
                "sk_dtfim": 20260131,
                "cd_compra": "c2",
                "sk_cliente": "cli-1",
                "vl_compra": 300.0,
                "nm_segmento": "Alimentação",
                "nm_fantasa": "Restaurante A",
                "bairro": "Centro",
                "cidade": "Goiânia",
                "nm_empreendimento": "Arca Parque",
            },
            {
                "cd_promocao": "P001",
                "nm_promocao": "Promoção Verão no Arca Parque 2026",
                "sk_dtinicio": 20260101,
                "sk_dtfim": 20260131,
                "cd_compra": "c3",
                "sk_cliente": "cli-2",
                "vl_compra": 200.0,
                "nm_segmento": "Moda",
                "nm_fantasa": "Loja B",
                "bairro": "Sul",
                "cidade": "Goiânia",
                "nm_empreendimento": "Arca Parque",
            },
        ]
        dataframe = pd.DataFrame(rows)
        if self._drop_columns:
            dataframe = dataframe.drop(columns=self._drop_columns)
        return {"Dados_copiloto": dataframe}


class MinimalCampaignDetailDataService:
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
                        "nm_promocao": "No Pelo 360 com Hugo e Guilherme e Buriti Shopping",
                        "vl_compra": 100.0,
                    },
                    {
                        "nm_promocao": "No Pelo 360 com Hugo e Guilherme e Buriti Shopping",
                        "vl_compra": 250.0,
                    },
                ],
            ),
        }


def _execution_service(
    *,
    data_service=None,
    drop_columns: list[str] | None = None,
) -> ExecutionService:
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
        data_service=data_service or CampaignDetailDataService(drop_columns=drop_columns),
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


def test_campaign_detail_returns_complete_executive_summary() -> None:
    response = _execution_service().execute_question(
        question="Pode detalhar a campanha Arcaparque?",
        knowledge_context=KnowledgeService().get_context(),
    )

    answer = response.answer.lower()

    assert "faturamento total" in answer
    assert "compras informadas" in answer
    assert "ticket médio por cliente" in answer
    assert "ticket médio por compra" in answer
    assert "segmento" in answer
    assert "alimentação" in answer
    assert "bairro" in answer
    assert "centro" in answer
    assert "cidade" in answer
    assert "goiânia" in answer
    assert "o indicador faturamento foi calculado" not in answer
    assert response.data[0]["faturamento_total"] == 600.0
    assert response.data[0]["quantidade_compras"] == 3


def test_campaign_detail_ignores_missing_optional_columns_without_technical_error() -> None:
    response = _execution_service(
        drop_columns=["cidade", "nm_empreendimento"],
    ).execute_question(
        question="Pode detalhar a campanha Arcaparque?",
        knowledge_context=KnowledgeService().get_context(),
    )

    answer = response.answer.lower()

    assert "default table does not contain" not in answer
    assert "status:" not in answer
    assert "intencao" not in answer
    assert "metricas" not in answer
    assert "operações" not in answer
    assert "faturamento total" in answer
    assert "compras informadas" in answer
    assert "ticket médio por cliente" in answer
    assert "ticket médio por compra" in answer
    assert "segmento" in answer
    assert "bairro" in answer
    assert "alguns campos não estavam disponíveis" in answer
    assert "cidade" in answer
    assert response.data[0]["faturamento_total"] == 600.0


def test_campaign_detail_executes_with_only_required_columns() -> None:
    response = _execution_service(
        data_service=MinimalCampaignDetailDataService(),
    ).execute_question(
        question="Olá, poderia por favor fazer um resumo da campanha no pelo?",
        knowledge_context=KnowledgeService().get_context(),
    )

    answer = response.answer.lower()

    assert "default table does not contain" not in answer
    assert "required_columns" not in answer
    assert "status:" not in answer
    assert "intencao" not in answer
    assert "operações" not in answer
    assert "faturamento total" in answer
    assert "r$ 350,00" in answer
    assert "alguns campos" in answer
    assert "dispon" in answer
    assert response.data[0]["faturamento_total"] == 350.0
    assert response.data[0]["quantidade_compras"] is None

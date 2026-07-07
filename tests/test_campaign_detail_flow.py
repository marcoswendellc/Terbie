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


ARCAPARQUE = "Promo\u00e7\u00e3o Ver\u00e3o no Arca Parque 2026"
NO_PELO = "No Pelo 360 com Hugo e Guilherme e Buriti Shopping"


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
        dataframe = pd.DataFrame(
            [
                self._row(100.0, "c1", "cli-1", "Alimenta\u00e7\u00e3o", "Restaurante A", "Centro", "Goi\u00e2nia"),
                self._row(300.0, "c2", "cli-1", "Alimenta\u00e7\u00e3o", "Restaurante A", "Centro", "Goi\u00e2nia"),
                self._row(200.0, "c3", "cli-2", "Moda", "Loja B", "Sul", "Goi\u00e2nia"),
            ],
        )
        if self._drop_columns:
            dataframe = dataframe.drop(columns=self._drop_columns)
        return {"Dados_copiloto": dataframe}

    def _row(
        self,
        value: float,
        purchase: str,
        customer: str,
        segment: str | None,
        store: str | None,
        neighborhood: str | None,
        city: str | None,
    ) -> dict[str, object]:
        return {
            "cd_promocao": "P001",
            "nm_promocao": ARCAPARQUE,
            "sk_dtinicio": 20260101,
            "sk_dtfim": 20260131,
            "cd_compra": purchase,
            "sk_cliente": customer,
            "vl_compra": value,
            "nm_segmento": segment,
            "nm_fantasa": store,
            "bairro": neighborhood,
            "cidade": city,
            "nm_empreendimento": "Arca Parque",
        }


class NullHeavyCampaignDetailDataService(CampaignDetailDataService):
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
                    self._row(100.0, "c1", "cli-1", "Alimenta\u00e7\u00e3o", "Restaurante A", "Centro", "Goi\u00e2nia"),
                    self._row(300.0, "c2", "cli-1", "Alimenta\u00e7\u00e3o", "Restaurante A", "Centro", "Goi\u00e2nia"),
                    self._row(200.0, "c3", "cli-2", "Moda", "Loja B", "Sul", "Goi\u00e2nia"),
                    self._row(1000.0, "c4", "cli-3", "NULL", "", "NULL", ""),
                ],
            ),
        }


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
                    {"nm_promocao": NO_PELO, "vl_compra": 100.0},
                    {"nm_promocao": NO_PELO, "vl_compra": 250.0},
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
    assert "ticket m\u00e9dio por cliente" in answer
    assert "ticket m\u00e9dio por compra" in answer
    assert "segmento" in answer
    assert "alimenta\u00e7\u00e3o" in answer
    assert "bairro" in answer
    assert "centro" in answer
    assert "cidade" in answer
    assert "goi\u00e2nia" in answer
    assert "o indicador faturamento foi calculado" not in answer
    assert "n\u00e3o identificado" not in answer
    assert "indispon" not in answer
    assert response.data[0]["faturamento_total"] == 600.0
    assert response.data[0]["quantidade_compras"] == 3


def test_campaign_detail_ignores_null_blank_and_null_text_rankings() -> None:
    response = _execution_service(
        data_service=NullHeavyCampaignDetailDataService(),
    ).execute_question(
        question="Pode detalhar a campanha Arcaparque?",
        knowledge_context=KnowledgeService().get_context(),
    )

    answer = response.answer.lower()

    assert "null" not in answer
    assert "n\u00e3o identificado" not in answer
    assert "indispon" not in answer
    assert response.data[0]["faturamento_total"] == 1600.0
    assert response.data[0]["quantidade_compras"] == 4
    assert response.data[0]["bairro_principal"] == "Centro"
    assert response.data[0]["segmento_principal"] == "Alimenta\u00e7\u00e3o"
    assert response.data[0]["loja_maior_faturamento"] == "Restaurante A"


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
    assert "opera\u00e7\u00f5es" not in answer
    assert "faturamento total" in answer
    assert "compras informadas" in answer
    assert "ticket m\u00e9dio por cliente" in answer
    assert "ticket m\u00e9dio por compra" in answer
    assert "segmento" in answer
    assert "bairro" in answer
    assert "alguns campos" not in answer
    assert "dispon" not in answer
    assert "cidade n\u00e3o identificada" not in answer
    assert response.data[0]["faturamento_total"] == 600.0


def test_campaign_detail_executes_with_only_required_columns() -> None:
    response = _execution_service(
        data_service=MinimalCampaignDetailDataService(),
    ).execute_question(
        question="Ol\u00e1, poderia por favor fazer um resumo da campanha no pelo?",
        knowledge_context=KnowledgeService().get_context(),
    )

    answer = response.answer.lower()

    assert "default table does not contain" not in answer
    assert "required_columns" not in answer
    assert "status:" not in answer
    assert "intencao" not in answer
    assert "opera\u00e7\u00f5es" not in answer
    assert "faturamento total" in answer
    assert "r$ 350,00" in answer
    assert "alguns campos" not in answer
    assert "dispon" not in answer
    assert response.data[0]["faturamento_total"] == 350.0
    assert response.data[0]["quantidade_compras"] is None

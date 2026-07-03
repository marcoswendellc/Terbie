from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from app.catalog.data_catalog import DataCatalog
from app.core.config import Settings
from app.core.exceptions import DataSourceError
from app.datasources.base import BaseTabularDataSource
from app.executor.models import ExecutionResult
from app.knowledge.knowledge_service import KnowledgeService
from app.narrator.models import NarratorResponse
from app.planner.models import ExecutionPlan
from app.schemas.discovery import SchemaDiscovery
from app.services.data_service import DataService
from app.services.execution_service import ExecutionService


class FakeTabularDataSource(BaseTabularDataSource):
    def get_name(self) -> str:
        return "google_sheets"

    def list_tables(self) -> list[str]:
        return ["Dados_copiloto", "Usuarios"]

    def load_table(self, table_name: str) -> pd.DataFrame:
        return self.read_sheet("spreadsheet-id", table_name)

    def read_sheet(self, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
        _ = spreadsheet_id
        return pd.DataFrame({"table_name": [sheet_name]})

    def read_spreadsheet(
        self,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        _ = spreadsheet_id
        return {
            sheet_name: pd.DataFrame({"table_name": [sheet_name]})
            for sheet_name in (sheet_names or ["Dados_copiloto"])
        }

    def list_sheet_names(self, spreadsheet_id: str) -> list[str]:
        _ = spreadsheet_id
        return ["Dados_copiloto", "Usuarios"]


class RecordingDataService:
    def __init__(self) -> None:
        self.sheet_names: list[str] | None = None

    def read_google_spreadsheet_data(
        self,
        *,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        _ = spreadsheet_id
        self.sheet_names = sheet_names
        return {
            "Dados_copiloto": pd.DataFrame(
                {
                    "nm_fantasa": ["A"],
                    "vl_compra": [100.0],
                    "Senha": ["never-return"],
                },
            ),
        }


class FailingDataService:
    def read_google_spreadsheet_data(self, **kwargs: Any) -> dict[str, pd.DataFrame]:
        _ = kwargs
        raise AssertionError("DataService should not be called for introduction questions")


class FakeSemanticService:
    def resolve(self, question: str) -> object:
        return {"question": question}


class FakePlannerService:
    def create_draft_plan(self, **kwargs: Any) -> object:
        _ = kwargs
        return SimpleNamespace(plan=ExecutionPlan())


class RecordingExecutor:
    def execute(self, **kwargs: Any) -> ExecutionResult:
        dataframe = kwargs["dataframe"]
        assert dataframe.attrs["table_name"] == "Dados_copiloto"
        return ExecutionResult(
            data=[
                {
                    "nm_fantasa": "A",
                    "faturamento": 100.0,
                    "Senha": "never-return",
                    "Password": "never-return",
                    "Token": "never-return",
                    "Secret": "never-return",
                },
            ],
            metadata={},
            statistics={},
            warnings=[],
            execution_time=0.01,
            rows_returned=1,
        )


class FakeNarratorService:
    def narrate(self, request: object) -> NarratorResponse:
        _ = request
        return NarratorResponse(answer="Resultado encontrado.", highlights=[])


def _execution_service(data_service: object) -> ExecutionService:
    return ExecutionService(
        settings=Settings(
            google_sheets_spreadsheet_id="spreadsheet-id",
            default_table="Dados_copiloto",
        ),
        semantic_service=FakeSemanticService(),
        planner_service=FakePlannerService(),
        data_service=data_service,
        executor=RecordingExecutor(),
        narrator_service=FakeNarratorService(),
    )


def test_execute_uses_default_table_dados_copiloto() -> None:
    data_service = RecordingDataService()
    response = _execution_service(data_service).execute_question(
        question="Quais são os 10 restaurantes com maior faturamento?",
        knowledge_context=KnowledgeService().get_context(),
    )

    assert data_service.sheet_names == ["Dados_copiloto"]
    assert response.metadata["selected_table"] == "Dados_copiloto"


def test_execute_introduction_question_does_not_query_any_table() -> None:
    response = _execution_service(FailingDataService()).execute_question(
        question="olá, te conheço?",
        knowledge_context=KnowledgeService().get_context(),
    )

    assert response.data == []
    assert response.metadata["data_accessed"] is False
    assert "Terbie" in response.answer


def test_blocked_table_access_returns_safe_error() -> None:
    service = DataService(
        data_source=FakeTabularDataSource(),
        schema_discovery=SchemaDiscovery(),
        data_catalog=DataCatalog(),
        default_table="Dados_copiloto",
        blocked_tables="Usuarios,Senhas,Credenciais,Tokens,Secrets",
    )

    with pytest.raises(DataSourceError) as exc_info:
        service.load_table(table_name="Usuarios")

    assert exc_info.value.status_code == 403
    assert "blocked by security policy" in exc_info.value.message


def test_execute_response_does_not_return_sensitive_columns() -> None:
    response = _execution_service(RecordingDataService()).execute_question(
        question="Quais são os 10 restaurantes com maior faturamento?",
        knowledge_context=KnowledgeService().get_context(),
    )

    assert response.data == [{"nm_fantasa": "A", "faturamento": 100.0}]
    assert not {"Senha", "Password", "Token", "Secret"}.intersection(response.data[0])

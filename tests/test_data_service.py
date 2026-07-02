from typing import Any

import pandas as pd

from app.catalog.data_catalog import DataCatalog
from app.datasources.base import BaseTabularDataSource
from app.schemas.discovery import SchemaDiscovery
from app.services.data_service import DataService


class FakeGoogleSheetsDataSource(BaseTabularDataSource):
    def read_sheet(self, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
        return self.read_spreadsheet(spreadsheet_id, [sheet_name])[sheet_name]

    def read_spreadsheet(
        self,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        _ = spreadsheet_id
        available_tables: dict[str, pd.DataFrame] = {
            "vendas": pd.DataFrame(
                {
                    "valor": ["10.5", "20.0", None],
                    "data": ["2026-01-01", "2026-01-02", None],
                    "ativo": ["true", "false", None],
                    "loja": ["A", "B", "A"],
                },
            ),
        }
        target_names = sheet_names or list(available_tables)
        return {sheet_name: available_tables[sheet_name] for sheet_name in target_names}

    def list_sheet_names(self, spreadsheet_id: str) -> list[str]:
        _ = spreadsheet_id
        return ["vendas"]


def test_load_google_spreadsheet_discovers_and_registers_schemas() -> None:
    catalog = DataCatalog()
    service = DataService(
        data_source=FakeGoogleSheetsDataSource(),
        schema_discovery=SchemaDiscovery(),
        data_catalog=catalog,
    )

    schemas = service.load_google_spreadsheet(spreadsheet_id="spreadsheet-id")

    assert [schema.name for schema in schemas] == ["vendas"]
    assert catalog.list_tables() == ["vendas"]

    schema = catalog.get_schema("vendas")
    assert schema is not None
    columns: dict[str, Any] = {
        column.name: column.model_dump(mode="json") for column in schema.columns
    }
    assert columns["valor"]["data_type"] == "number"
    assert columns["valor"]["null_count"] == 1
    assert columns["data"]["data_type"] == "datetime"
    assert columns["ativo"]["data_type"] == "boolean"
    assert columns["loja"]["examples"] == ["A", "B"]

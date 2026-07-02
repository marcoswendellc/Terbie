import pandas as pd

from app.catalog.data_catalog import DataCatalog
from app.datasources.base import BaseTabularDataSource
from app.models.schema import DataCatalogEntry, TableSchema
from app.schemas.discovery import SchemaDiscovery


class DataService:
    """Coordinates data loading, schema discovery, and catalog registration."""

    def __init__(
        self,
        data_source: BaseTabularDataSource,
        schema_discovery: SchemaDiscovery,
        data_catalog: DataCatalog,
    ) -> None:
        self._data_source = data_source
        self._schema_discovery = schema_discovery
        self._data_catalog = data_catalog

    def load_google_sheet_table(
        self,
        *,
        spreadsheet_id: str,
        sheet_name: str,
        table_name: str | None = None,
    ) -> TableSchema:
        data_frame = self._data_source.read_sheet(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
        )
        resolved_table_name = table_name or sheet_name
        schema = self._schema_discovery.discover(
            table_name=resolved_table_name,
            data_frame=data_frame,
        )
        self._data_catalog.register_table(
            DataCatalogEntry(
                table_name=resolved_table_name,
                table_schema=schema,
                source=f"google_sheets:{spreadsheet_id}:{sheet_name}",
            ),
        )
        return schema

    def load_google_spreadsheet(
        self,
        *,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> list[TableSchema]:
        tables = self._data_source.read_spreadsheet(
            spreadsheet_id=spreadsheet_id,
            sheet_names=sheet_names,
        )
        schemas: list[TableSchema] = []

        for sheet_name, data_frame in tables.items():
            schema = self._schema_discovery.discover(table_name=sheet_name, data_frame=data_frame)
            self._data_catalog.register_table(
                DataCatalogEntry(
                    table_name=sheet_name,
                    table_schema=schema,
                    source=f"google_sheets:{spreadsheet_id}:{sheet_name}",
                ),
            )
            schemas.append(schema)

        return schemas

    def read_google_spreadsheet_data(
        self,
        *,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        return self._data_source.read_spreadsheet(
            spreadsheet_id=spreadsheet_id,
            sheet_names=sheet_names,
        )

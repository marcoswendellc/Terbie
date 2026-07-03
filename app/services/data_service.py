from http import HTTPStatus

import pandas as pd

from app.catalog.data_catalog import DataCatalog
from app.core.exceptions import DataSourceError
from app.datasources.base import BaseDataSource, BaseTabularDataSource
from app.datasources.models import DataSourceHealth, DataSourceInfo
from app.datasources.registry import DataSourceRegistry
from app.models.schema import DataCatalogEntry, TableSchema
from app.schemas.discovery import SchemaDiscovery


class DataService:
    """Coordinates data loading, schema discovery, and catalog registration."""

    def __init__(
        self,
        schema_discovery: SchemaDiscovery,
        data_catalog: DataCatalog,
        datasource_registry: DataSourceRegistry | None = None,
        data_source: BaseTabularDataSource | None = None,
        default_datasource: str = "google_sheets",
        default_table: str = "Dados_copiloto",
        blocked_tables: str | list[str] | None = None,
    ) -> None:
        if datasource_registry is None:
            datasource_registry = DataSourceRegistry(default_name=default_datasource)
            if data_source is not None:
                datasource_registry.register(default_datasource, data_source)

        self._datasource_registry = datasource_registry
        self._schema_discovery = schema_discovery
        self._data_catalog = data_catalog
        self._default_table = default_table
        self._blocked_tables = self._normalize_table_names(blocked_tables)

    def list_datasources(self) -> list[DataSourceInfo]:
        infos: list[DataSourceInfo] = []
        for datasource in self._datasource_registry.list():
            name = datasource.get_name()
            try:
                healthy = datasource.health_check()
            except Exception:  # noqa: BLE001
                healthy = False
            tables = self._safe_list_tables(datasource=datasource) if healthy else []
            infos.append(
                DataSourceInfo(
                    name=name,
                    type=name,
                    tables=tables,
                    healthy=healthy,
                ),
            )
        return infos

    def check_datasource_health(self) -> list[DataSourceHealth]:
        health: list[DataSourceHealth] = []
        for datasource in self._datasource_registry.list():
            try:
                healthy = datasource.health_check()
            except Exception as exc:  # noqa: BLE001
                health.append(
                    DataSourceHealth(
                        name=datasource.get_name(),
                        healthy=False,
                        message=str(exc),
                    ),
                )
                continue

            health.append(
                DataSourceHealth(
                    name=datasource.get_name(),
                    healthy=healthy,
                    message=None if healthy else "Data source health check failed.",
                ),
            )
        return health

    def list_tables(self, datasource_name: str | None = None) -> list[str]:
        datasource = self._resolve_datasource(datasource_name=datasource_name)
        return [
            table_name
            for table_name in datasource.list_tables()
            if self._is_table_allowed(table_name)
        ]

    def load_table(
        self,
        *,
        table_name: str | None = None,
        datasource_name: str | None = None,
    ) -> TableSchema:
        table_name = self._resolve_table_name(table_name)
        datasource = self._resolve_datasource(datasource_name=datasource_name)
        data_frame = datasource.load_table(table_name)
        if not isinstance(data_frame, pd.DataFrame):
            raise DataSourceError(
                "Data source returned an unsupported table payload",
                details={"datasource_name": datasource.get_name(), "table_name": table_name},
            )

        schema = self._schema_discovery.discover(table_name=table_name, data_frame=data_frame)
        self._data_catalog.register_table(
            DataCatalogEntry(
                table_name=table_name,
                table_schema=schema,
                source=f"{datasource.get_name()}:{table_name}",
                datasource_name=datasource.get_name(),
            ),
        )
        return schema

    def get_table_schema(
        self,
        *,
        table_name: str | None = None,
        datasource_name: str | None = None,
    ) -> TableSchema:
        table_name = self._resolve_table_name(table_name)
        datasource = self._resolve_datasource(datasource_name=datasource_name)
        schema = self._data_catalog.get_schema(
            table_name,
            datasource_name=datasource.get_name(),
        )
        if schema is not None:
            return schema

        return self.load_table(
            table_name=table_name,
            datasource_name=datasource.get_name(),
        )

    def load_google_sheet_table(
        self,
        *,
        spreadsheet_id: str,
        sheet_name: str | None = None,
        table_name: str | None = None,
    ) -> TableSchema:
        sheet_name = self._resolve_table_name(sheet_name)
        data_frame = self._google_sheets_data_source().read_sheet(
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
                datasource_name="google_sheets",
            ),
        )
        return schema

    def load_google_spreadsheet(
        self,
        *,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> list[TableSchema]:
        sheet_names = self._resolve_sheet_names(sheet_names)
        tables = self._google_sheets_data_source().read_spreadsheet(
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
                    datasource_name="google_sheets",
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
        sheet_names = self._resolve_sheet_names(sheet_names)
        return self._google_sheets_data_source().read_spreadsheet(
            spreadsheet_id=spreadsheet_id,
            sheet_names=sheet_names,
        )

    def _resolve_datasource(self, datasource_name: str | None = None) -> BaseDataSource:
        if datasource_name is None:
            return self._datasource_registry.default()
        return self._datasource_registry.get(datasource_name)

    def _google_sheets_data_source(self) -> BaseTabularDataSource:
        datasource = self._datasource_registry.get("google_sheets")
        if not isinstance(datasource, BaseTabularDataSource):
            raise DataSourceError(
                "Configured Google Sheets data source is not tabular",
                details={"datasource_name": datasource.get_name()},
            )
        return datasource

    def _safe_list_tables(self, *, datasource: BaseDataSource) -> list[str]:
        try:
            return [
                table_name
                for table_name in datasource.list_tables()
                if self._is_table_allowed(table_name)
            ]
        except Exception:  # noqa: BLE001
            return []

    def _resolve_table_name(self, table_name: str | None) -> str:
        resolved_table_name = table_name or self._default_table
        self._ensure_table_allowed(resolved_table_name)
        return resolved_table_name

    def _resolve_sheet_names(self, sheet_names: list[str] | None) -> list[str]:
        resolved_sheet_names = sheet_names or [self._default_table]
        for sheet_name in resolved_sheet_names:
            self._ensure_table_allowed(sheet_name)
        return resolved_sheet_names

    def _ensure_table_allowed(self, table_name: str) -> None:
        if self._is_table_allowed(table_name):
            return

        raise DataSourceError(
            "Table access is blocked by security policy",
            status_code=HTTPStatus.FORBIDDEN,
            details={"table_name": table_name},
        )

    def _is_table_allowed(self, table_name: str) -> bool:
        return self._normalize_table_name(table_name) not in self._blocked_tables

    def _normalize_table_names(self, table_names: str | list[str] | None) -> set[str]:
        if table_names is None:
            return set()
        if isinstance(table_names, str):
            table_names = table_names.split(",")
        return {
            self._normalize_table_name(table_name)
            for table_name in table_names
            if table_name.strip()
        }

    def _normalize_table_name(self, table_name: str) -> str:
        return table_name.strip().casefold()

from app.core.config import Settings
from app.datasources.google_sheets import GoogleSheetsDataSource
from app.datasources.csv import CSVDataSource
from app.datasources.excel import ExcelDataSource
from app.datasources.registry import DataSourceRegistry


class DataSourceFactory:
    """Builds configured Terbie data sources."""

    def create_registry(self, settings: Settings) -> DataSourceRegistry:
        registry = DataSourceRegistry(default_name=settings.default_datasource)
        registry.register("google_sheets", GoogleSheetsDataSource(settings=settings))
        registry.register("csv", CSVDataSource(settings.local_data_path))
        registry.register("excel", ExcelDataSource(settings.local_data_path))

        # Future sources:
        # - sqlserver: SQLServerDataSource
        # - postgres: PostgresDataSource
        # - bigquery: BigQueryDataSource
        # - csv: CSVDataSource
        # - excel: ExcelDataSource
        return registry

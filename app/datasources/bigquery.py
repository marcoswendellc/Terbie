from typing import Any

from app.datasources.base import BaseDataSource


class BigQueryDataSource(BaseDataSource):
    def get_name(self) -> str:
        return "bigquery"

    def list_tables(self) -> list[str]:
        raise NotImplementedError("BigQueryDataSource ainda não foi implementado.")

    def load_table(self, table_name: str) -> Any:
        raise NotImplementedError("BigQueryDataSource ainda não foi implementado.")

    def get_schema(self, table_name: str) -> Any:
        raise NotImplementedError("BigQueryDataSource ainda não foi implementado.")

    def health_check(self) -> bool:
        raise NotImplementedError("BigQueryDataSource ainda não foi implementado.")

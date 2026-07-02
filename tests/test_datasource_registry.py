import pandas as pd

from app.datasources.base import BaseDataSource
from app.datasources.registry import DataSourceRegistry


class FakeDataSource(BaseDataSource):
    def get_name(self) -> str:
        return "fake"

    def list_tables(self) -> list[str]:
        return ["vendas"]

    def load_table(self, table_name: str) -> pd.DataFrame:
        return pd.DataFrame({"table": [table_name]})

    def get_schema(self, table_name: str) -> dict[str, str]:
        return {"table_name": table_name}

    def health_check(self) -> bool:
        return True


def test_datasource_registry_registers_and_returns_datasource() -> None:
    datasource = FakeDataSource()
    registry = DataSourceRegistry(default_name="fake")

    registry.register("fake", datasource)

    assert registry.get("fake") is datasource
    assert registry.exists("fake") is True


def test_datasource_registry_returns_default_datasource() -> None:
    datasource = FakeDataSource()
    registry = DataSourceRegistry(default_name="fake")
    registry.register("fake", datasource)

    assert registry.default() is datasource

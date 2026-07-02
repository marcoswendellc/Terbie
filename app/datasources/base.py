from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd


class BaseDataSource(ABC):
    """Generic contract for every Terbie data source."""

    @abstractmethod
    def get_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def list_tables(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def load_table(self, table_name: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def get_schema(self, table_name: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        raise NotImplementedError


class BaseTabularDataSource(BaseDataSource):
    """Contract for tabular data sources that expose sheets/tables as DataFrames."""

    def get_name(self) -> str:
        return self.__class__.__name__

    def list_tables(self) -> list[str]:
        return []

    def load_table(self, table_name: str) -> pd.DataFrame:
        raise NotImplementedError("This tabular data source requires source-specific loading.")

    def get_schema(self, table_name: str) -> Any:
        dataframe = self.load_table(table_name)
        return {
            "table_name": table_name,
            "columns": list(dataframe.columns),
            "dtypes": {column: str(dtype) for column, dtype in dataframe.dtypes.items()},
        }

    def health_check(self) -> bool:
        return True

    @abstractmethod
    def read_sheet(self, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def read_spreadsheet(
        self,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        raise NotImplementedError

    @abstractmethod
    def list_sheet_names(self, spreadsheet_id: str) -> list[str]:
        raise NotImplementedError

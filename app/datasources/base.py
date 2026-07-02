from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


class BaseTabularDataSource(ABC):
    """Contract for tabular data sources that expose sheets/tables as DataFrames."""

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

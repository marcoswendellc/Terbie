from pathlib import Path

import pandas as pd

from app.core.exceptions import ConfigurationError, DataSourceError
from app.datasources.base import BaseTabularDataSource


class ExcelDataSource(BaseTabularDataSource):
    def __init__(self, workbook: str | Path | None) -> None:
        self._workbook = Path(workbook).resolve() if workbook else None

    def get_name(self) -> str:
        return "excel"

    def list_tables(self) -> list[str]:
        return pd.ExcelFile(self._required_workbook()).sheet_names

    def load_table(self, table_name: str) -> pd.DataFrame:
        if table_name not in self.list_tables():
            raise DataSourceError("Planilha não encontrada.", details={"table": table_name})
        return pd.read_excel(self._required_workbook(), sheet_name=table_name)

    def health_check(self) -> bool:
        return self._workbook is not None and self._workbook.is_file()

    def read_sheet(self, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
        return self.load_table(sheet_name)

    def read_spreadsheet(self, spreadsheet_id: str, sheet_names: list[str] | None = None) -> dict[str, pd.DataFrame]:
        names = sheet_names or self.list_tables()
        return {name: self.load_table(name) for name in names}

    def list_sheet_names(self, spreadsheet_id: str) -> list[str]:
        return self.list_tables()

    def _required_workbook(self) -> Path:
        if self._workbook is None or not self._workbook.is_file():
            raise ConfigurationError("LOCAL_DATA_PATH não aponta para um arquivo Excel válido.")
        return self._workbook

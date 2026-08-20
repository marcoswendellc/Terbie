from pathlib import Path

import pandas as pd

from app.core.exceptions import ConfigurationError, DataSourceError
from app.datasources.base import BaseTabularDataSource


class CSVDataSource(BaseTabularDataSource):
    def __init__(self, root: str | Path | None) -> None:
        self._root = Path(root).resolve() if root else None

    def get_name(self) -> str:
        return "csv"

    def list_tables(self) -> list[str]:
        root = self._required_root()
        return sorted(path.stem for path in root.glob("*.csv") if path.is_file())

    def load_table(self, table_name: str) -> pd.DataFrame:
        path = self._safe_path(table_name, ".csv")
        try:
            return pd.read_csv(path)
        except (OSError, ValueError) as exc:
            raise DataSourceError("Não foi possível ler o arquivo CSV.", details={"table": table_name}) from exc

    def health_check(self) -> bool:
        return self._root is not None and self._root.is_dir()

    def read_sheet(self, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
        return self.load_table(sheet_name)

    def read_spreadsheet(self, spreadsheet_id: str, sheet_names: list[str] | None = None) -> dict[str, pd.DataFrame]:
        names = sheet_names or self.list_tables()
        return {name: self.load_table(name) for name in names}

    def list_sheet_names(self, spreadsheet_id: str) -> list[str]:
        return self.list_tables()

    def _required_root(self) -> Path:
        if self._root is None or not self._root.is_dir():
            raise ConfigurationError("LOCAL_DATA_PATH não aponta para um diretório válido.")
        return self._root

    def _safe_path(self, table_name: str, suffix: str) -> Path:
        root = self._required_root()
        if not table_name or Path(table_name).name != table_name:
            raise DataSourceError("Nome de tabela local inválido.")
        path = (root / f"{table_name}{suffix}").resolve()
        if path.parent != root or not path.is_file():
            raise DataSourceError("Tabela local não encontrada.", details={"table": table_name})
        return path

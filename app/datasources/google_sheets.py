from __future__ import annotations

import json
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, DataSourceError, TerbieError
from app.datasources.base import BaseTabularDataSource

if TYPE_CHECKING:
    import gspread
    import pandas as pd
    from gspread import Spreadsheet


class GoogleSheetsDataSource(BaseTabularDataSource):
    """Reads raw tabular data from Google Sheets."""

    _SCOPES = ("https://www.googleapis.com/auth/spreadsheets.readonly",)
    _NAME = "google_sheets"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_name(self) -> str:
        return self._NAME

    def list_tables(self) -> list[str]:
        return self.list_sheet_names(self._default_spreadsheet_id())

    def load_table(self, table_name: str) -> pd.DataFrame:
        return self.read_sheet(
            spreadsheet_id=self._default_spreadsheet_id(),
            sheet_name=table_name,
        )

    def health_check(self) -> bool:
        try:
            self.list_tables()
        except (TerbieError, ValueError):
            return False
        return True

    def read_sheet(self, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
        spreadsheet = self.open_spreadsheet(spreadsheet_id)
        worksheet = self._worksheet(spreadsheet=spreadsheet, sheet_name=sheet_name)
        values = worksheet.get_all_values()
        return self._values_to_data_frame(values)

    def read_spreadsheet(
        self,
        spreadsheet_id: str,
        sheet_names: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        spreadsheet = self.open_spreadsheet(spreadsheet_id)
        target_names = sheet_names or self.list_sheet_names(spreadsheet_id)
        return {
            sheet_name: self._worksheet_to_data_frame(
                spreadsheet=spreadsheet,
                sheet_name=sheet_name,
            )
            for sheet_name in target_names
        }

    def list_sheet_names(self, spreadsheet_id: str) -> list[str]:
        spreadsheet = self.open_spreadsheet(spreadsheet_id)
        return [worksheet.title for worksheet in spreadsheet.worksheets()]

    def open_spreadsheet(self, spreadsheet_id: str) -> Spreadsheet:
        import gspread

        try:
            return self._client().open_by_key(spreadsheet_id)
        except gspread.exceptions.SpreadsheetNotFound as exc:
            raise DataSourceError(
                "Google Sheets spreadsheet was not found or is not shared with the service account",
                details={"spreadsheet_id": spreadsheet_id},
            ) from exc
        except gspread.exceptions.APIError as exc:
            raise DataSourceError(
                "Google Sheets API request failed",
                details={"spreadsheet_id": spreadsheet_id},
            ) from exc

    def _client(self) -> gspread.Client:
        import gspread
        from google.oauth2.service_account import Credentials

        service_account_json = self._settings.google_service_account_json
        if service_account_json is None:
            raise ConfigurationError(
                "Google Sheets credentials are not configured",
                details={"expected": "GOOGLE_SERVICE_ACCOUNT_JSON"},
            )

        try:
            service_account_info = json.loads(service_account_json.get_secret_value())
        except JSONDecodeError as exc:
            raise ConfigurationError(
                "Google Sheets service account JSON is invalid",
                details={"expected": "Valid JSON in GOOGLE_SERVICE_ACCOUNT_JSON"},
            ) from exc

        if not isinstance(service_account_info, dict):
            raise ConfigurationError(
                "Google Sheets service account JSON must be an object",
                details={"expected": "JSON object in GOOGLE_SERVICE_ACCOUNT_JSON"},
            )

        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=self._SCOPES,
        )
        return gspread.authorize(credentials)

    def _values_to_data_frame(self, values: list[list[Any]]) -> pd.DataFrame:
        import pandas as pd

        if not values:
            return pd.DataFrame()

        header, *rows = values
        columns = self._normalize_columns(header)
        normalized_rows = [self._normalize_row(row=row, column_count=len(columns)) for row in rows]
        data_frame = pd.DataFrame(normalized_rows, columns=columns)
        return data_frame.replace("", pd.NA)

    def _worksheet_to_data_frame(
        self,
        *,
        spreadsheet: Spreadsheet,
        sheet_name: str,
    ) -> pd.DataFrame:
        worksheet = self._worksheet(spreadsheet=spreadsheet, sheet_name=sheet_name)
        return self._values_to_data_frame(worksheet.get_all_values())

    def _worksheet(self, *, spreadsheet: Spreadsheet, sheet_name: str) -> Any:
        import gspread

        try:
            return spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound as exc:
            raise DataSourceError(
                "Google Sheets worksheet was not found",
                details={"sheet_name": sheet_name},
            ) from exc

    def _normalize_columns(self, header: list[Any]) -> list[str]:
        columns: list[str] = []
        seen: dict[str, int] = {}

        for index, value in enumerate(header):
            base_name = str(value).strip() or f"column_{index + 1}"
            seen[base_name] = seen.get(base_name, 0) + 1
            column_name = base_name if seen[base_name] == 1 else f"{base_name}_{seen[base_name]}"
            columns.append(column_name)

        return columns

    def _normalize_row(self, *, row: list[Any], column_count: int) -> list[Any]:
        if len(row) >= column_count:
            return row[:column_count]

        return [*row, *([""] * (column_count - len(row)))]

    def _default_spreadsheet_id(self) -> str:
        spreadsheet_id = self._settings.google_sheets_spreadsheet_id
        if spreadsheet_id is None or spreadsheet_id.strip() == "":
            raise ConfigurationError(
                "Google Sheets spreadsheet ID is not configured",
                details={"expected": "GOOGLE_SHEETS_SPREADSHEET_ID"},
            )
        return spreadsheet_id

import pytest

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.datasources.google_sheets import GoogleSheetsDataSource


def test_google_sheets_datasource_requires_service_account_json() -> None:
    data_source = GoogleSheetsDataSource(settings=Settings(google_service_account_json=None))

    with pytest.raises(ConfigurationError) as exc_info:
        data_source.list_sheet_names("spreadsheet-id")

    assert "credentials are not configured" in exc_info.value.message
    assert exc_info.value.details == {"expected": "GOOGLE_SERVICE_ACCOUNT_JSON"}


def test_google_sheets_datasource_rejects_invalid_service_account_json() -> None:
    data_source = GoogleSheetsDataSource(settings=Settings(google_service_account_json="not-json"))

    with pytest.raises(ConfigurationError) as exc_info:
        data_source.list_sheet_names("spreadsheet-id")

    assert "service account JSON is invalid" in exc_info.value.message
    assert exc_info.value.details == {"expected": "Valid JSON in GOOGLE_SERVICE_ACCOUNT_JSON"}

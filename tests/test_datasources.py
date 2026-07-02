import pytest

from app.datasources.base import BaseDataSource
from app.datasources.google_sheets import GoogleSheetsDataSource
from app.datasources.sqlserver import SQLServerDataSource


def test_google_sheets_datasource_implements_base_datasource() -> None:
    assert issubclass(GoogleSheetsDataSource, BaseDataSource)


def test_sqlserver_placeholder_raises_not_implemented_error() -> None:
    datasource = SQLServerDataSource()

    with pytest.raises(NotImplementedError) as exc_info:
        datasource.list_tables()

    assert "SQLServerDataSource ainda não foi implementado" in str(exc_info.value)

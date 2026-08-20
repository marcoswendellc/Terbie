import pytest

from app.core.exceptions import DataSourceError
from app.datasources.csv import CSVDataSource
from app.datasources.excel import ExcelDataSource


def test_csv_datasource_lists_and_loads_safe_local_tables(tmp_path) -> None:
    (tmp_path / "compras.csv").write_text("shopping,valor\nSul,10\n", encoding="utf-8")
    datasource = CSVDataSource(tmp_path)

    assert datasource.list_tables() == ["compras"]
    assert datasource.load_table("compras").iloc[0].to_dict() == {
        "shopping": "Sul",
        "valor": 10,
    }
    with pytest.raises(DataSourceError):
        datasource.load_table("../segredo")


def test_excel_datasource_lists_and_loads_sheets(tmp_path) -> None:
    pandas = pytest.importorskip("pandas")
    path = tmp_path / "dados.xlsx"
    pandas.DataFrame([{"shopping": "Sul", "valor": 10}]).to_excel(
        path,
        sheet_name="compras",
        index=False,
    )
    datasource = ExcelDataSource(path)

    assert datasource.list_tables() == ["compras"]
    assert datasource.load_table("compras").iloc[0]["shopping"] == "Sul"

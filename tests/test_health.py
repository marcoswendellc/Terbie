from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.dependencies import provide_data_catalog, provide_data_service, provide_settings
from app.datasources.models import DataSourceHealth, DataSourceInfo
from app.main import app
from app.models.schema import ColumnSchema, DataCatalogEntry, TableSchema


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "Terbie"}


def test_tables_endpoint_returns_registered_tables() -> None:
    catalog = provide_data_catalog()
    catalog.register_table(
        DataCatalogEntry(
            table_name="vendas",
            table_schema=TableSchema(
                name="vendas",
                row_count=1,
                columns=[
                    ColumnSchema(
                        name="valor",
                        data_type="number",
                        nullable=False,
                        null_count=0,
                        unique_count=1,
                        min_value=10.0,
                        max_value=10.0,
                        examples=[10.0],
                    ),
                ],
            ),
            source="test",
        ),
    )
    client = TestClient(app)

    response = client.get("/tables")

    assert response.status_code == 200
    assert "vendas" in response.json()


def test_schema_endpoint_returns_registered_schema() -> None:
    client = TestClient(app)

    response = client.get("/schema/vendas")

    assert response.status_code == 200
    assert response.json()["name"] == "vendas"
    assert response.json()["columns"][0]["name"] == "valor"


def test_load_google_sheets_uses_default_spreadsheet_id_from_settings() -> None:
    class FakeDataService:
        spreadsheet_id: str | None = None
        sheet_names: list[str] | None = None

        def load_google_spreadsheet(
            self,
            *,
            spreadsheet_id: str,
            sheet_names: list[str] | None = None,
        ) -> list[TableSchema]:
            self.spreadsheet_id = spreadsheet_id
            self.sheet_names = sheet_names
            return [TableSchema(name="vendas", row_count=0, columns=[])]

    fake_data_service = FakeDataService()
    app.dependency_overrides[provide_data_service] = lambda: fake_data_service
    app.dependency_overrides[provide_settings] = lambda: Settings(
        google_sheets_spreadsheet_id="spreadsheet-from-env",
    )

    try:
        client = TestClient(app)
        response = client.post("/sources/google-sheets/load", json={"sheet_names": ["vendas"]})
    finally:
        app.dependency_overrides.pop(provide_data_service, None)
        app.dependency_overrides.pop(provide_settings, None)

    assert response.status_code == 200
    assert response.json()[0]["name"] == "vendas"
    assert fake_data_service.spreadsheet_id == "spreadsheet-from-env"
    assert fake_data_service.sheet_names == ["vendas"]


def test_datasources_endpoint_returns_registered_sources() -> None:
    class FakeDataService:
        def list_datasources(self) -> list[DataSourceInfo]:
            return [
                DataSourceInfo(
                    name="google_sheets",
                    type="google_sheets",
                    tables=["vendas"],
                    healthy=True,
                ),
            ]

    app.dependency_overrides[provide_data_service] = lambda: FakeDataService()
    try:
        client = TestClient(app)
        response = client.get("/datasources")
    finally:
        app.dependency_overrides.pop(provide_data_service, None)

    assert response.status_code == 200
    assert response.json()[0]["name"] == "google_sheets"


def test_datasources_health_endpoint_returns_registered_sources_health() -> None:
    class FakeDataService:
        def check_datasource_health(self) -> list[DataSourceHealth]:
            return [DataSourceHealth(name="google_sheets", healthy=True)]

    app.dependency_overrides[provide_data_service] = lambda: FakeDataService()
    try:
        client = TestClient(app)
        response = client.get("/datasources/health")
    finally:
        app.dependency_overrides.pop(provide_data_service, None)

    assert response.status_code == 200
    assert response.json() == [{"name": "google_sheets", "healthy": True, "message": None}]

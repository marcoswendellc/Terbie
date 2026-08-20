import pandas as pd

from app.core.config import Settings
from app.datasources.base import BaseTabularDataSource
from app.services.auth_service import AuthService


class FakeUsersDataSource(BaseTabularDataSource):
    def get_name(self) -> str:
        return "fake"

    def list_tables(self) -> list[str]:
        return ["Usuarios_Terbie"]

    def load_table(self, table_name: str) -> pd.DataFrame:
        return self.read_sheet("spreadsheet-id", table_name)

    def health_check(self) -> bool:
        return True

    def read_sheet(self, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
        assert spreadsheet_id == "spreadsheet-id"
        assert sheet_name == "Usuarios_Terbie"
        return pd.DataFrame(
            [{"cd_usuario": "7", "nm_usuario": "marco", "nm_senha": "segredo"}]
        )

    def read_spreadsheet(self, spreadsheet_id: str, sheet_names=None):
        return {"Usuarios_Terbie": self.read_sheet(spreadsheet_id, "Usuarios_Terbie")}

    def list_sheet_names(self, spreadsheet_id: str) -> list[str]:
        return ["Usuarios_Terbie"]


def make_service() -> AuthService:
    return AuthService(
        settings=Settings(google_sheets_spreadsheet_id="spreadsheet-id"),
        data_source=FakeUsersDataSource(),
    )


def test_authenticates_user_from_users_sheet() -> None:
    result = make_service().authenticate(username=" marco ", password="segredo")

    assert result.authenticated is True
    assert result.cd_usuario == "7"
    assert result.nm_usuario == "marco"
    assert result.access_token
    assert make_service().verify_token(result.access_token) is not None


def test_rejects_invalid_password_without_returning_user_data() -> None:
    result = make_service().authenticate(username="marco", password="incorreta")

    assert result.authenticated is False
    assert result.cd_usuario is None
    assert result.nm_usuario is None


def test_production_rejects_legacy_plaintext_passwords() -> None:
    service = AuthService(
        settings=Settings(
            environment="production",
            google_sheets_spreadsheet_id="spreadsheet-id",
            session_secret="production-test-secret",
        ),
        data_source=FakeUsersDataSource(),
    )

    assert service.authenticate(username="marco", password="segredo").authenticated is False

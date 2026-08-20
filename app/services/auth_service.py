from hmac import compare_digest
from hashlib import pbkdf2_hmac
from base64 import b64decode
from binascii import Error as Base64Error

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, DataSourceError
from app.datasources.base import BaseTabularDataSource
from app.models.auth import LoginResponse


class AuthService:
    _USERS_SHEET = "Usuarios_Terbie"
    _REQUIRED_COLUMNS = {"cd_usuario", "nm_usuario", "nm_senha"}

    def __init__(
        self,
        *,
        settings: Settings,
        data_source: BaseTabularDataSource,
    ) -> None:
        self._settings = settings
        self._data_source = data_source

    def authenticate(self, *, username: str, password: str) -> LoginResponse:
        spreadsheet_id = self._settings.google_sheets_spreadsheet_id
        if spreadsheet_id is None or not spreadsheet_id.strip():
            raise ConfigurationError(
                "Google Sheets spreadsheet ID is not configured",
                details={"expected": "GOOGLE_SHEETS_SPREADSHEET_ID"},
            )

        users = self._data_source.read_sheet(
            spreadsheet_id=spreadsheet_id,
            sheet_name=self._USERS_SHEET,
        )
        missing_columns = self._REQUIRED_COLUMNS.difference(users.columns)
        if missing_columns:
            raise DataSourceError(
                "The users worksheet has an invalid structure",
                details={"missing_columns": sorted(missing_columns)},
            )

        normalized_username = username.strip()
        for row in users.loc[:, ["cd_usuario", "nm_usuario", "nm_senha"]].itertuples(
            index=False,
            name=None,
        ):
            user_id, stored_username, stored_password = row
            candidate_username = "" if stored_username is None else str(stored_username).strip()
            candidate_password = "" if stored_password is None else str(stored_password)
            if compare_digest(candidate_username, normalized_username) and self._verify_password(
                password,
                candidate_password,
            ):
                return LoginResponse(
                    authenticated=True,
                    cd_usuario=None if user_id is None else str(user_id),
                    nm_usuario=candidate_username,
                )

        return LoginResponse(authenticated=False)

    def _verify_password(self, provided: str, stored: str) -> bool:
        if not stored.startswith("pbkdf2_sha256$"):
            return compare_digest(stored, provided)
        try:
            _, iterations, salt, encoded_hash = stored.split("$", maxsplit=3)
            calculated = pbkdf2_hmac(
                "sha256",
                provided.encode("utf-8"),
                b64decode(salt),
                int(iterations),
            )
            return compare_digest(calculated, b64decode(encoded_hash))
        except (ValueError, TypeError, Base64Error):
            return False

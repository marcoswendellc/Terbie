from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = Field(default="Terbie", alias="APP_NAME")
    environment: Literal["local", "development", "staging", "production", "test"] = Field(
        default="local",
        alias="ENVIRONMENT",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    google_service_account_json: SecretStr | None = Field(
        default=None,
        alias="GOOGLE_SERVICE_ACCOUNT_JSON",
    )
    google_sheets_spreadsheet_id: str | None = Field(
        default=None,
        alias="GOOGLE_SHEETS_SPREADSHEET_ID",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

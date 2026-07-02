from http import HTTPStatus
from typing import Any


class TerbieError(Exception):
    """Base class for application-level exceptions."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ConfigurationError(TerbieError):
    """Raised when the application cannot be configured correctly."""


class ServiceError(TerbieError):
    """Raised when an application service fails."""


class DataSourceError(TerbieError):
    """Raised when a configured data source cannot be accessed."""

from app.core.config import Settings
from app.models.health import HealthResponse


class HealthService:
    """Application service responsible for reporting system health."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_health(self) -> HealthResponse:
        return HealthResponse(status="ok", app=self._settings.app_name)

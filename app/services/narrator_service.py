from app.narrator.models import NarratorRequest, NarratorResponse
from app.narrator.narrator import TerbieNarrator


class NarratorService:
    """Application service for deterministic narration."""

    def __init__(self, narrator: TerbieNarrator) -> None:
        self._narrator = narrator

    def narrate(self, request: NarratorRequest) -> NarratorResponse:
        return self._narrator.narrate(request)

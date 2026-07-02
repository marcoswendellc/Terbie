from app.semantic.models import SemanticResolution
from app.semantic.resolver import SemanticResolver


class SemanticService:
    """Application service for deterministic semantic resolution."""

    def __init__(self, resolver: SemanticResolver) -> None:
        self._resolver = resolver

    def resolve(self, question: str) -> SemanticResolution:
        return self._resolver.resolve(question)

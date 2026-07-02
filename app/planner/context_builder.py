from typing import Any

from app.semantic.models import SemanticResolution


class PlannerContextBuilder:
    """Builds structured context for future planner implementations."""

    def build(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "question": question,
            "semantic_resolution": semantic_resolution.model_dump(mode="json"),
            "schema": schema or {},
        }

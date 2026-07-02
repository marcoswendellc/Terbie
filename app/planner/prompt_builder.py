from typing import Any

from app.semantic.models import SemanticResolution


class PlannerPromptBuilder:
    """Builds the future LLM prompt structure without calling an LLM."""

    def build(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution,
        schema: dict[str, Any] | None = None,
    ) -> str:
        schema_text = schema if schema is not None else {}
        return (
            "You are Terbie Planner.\n"
            f"Question: {question}\n"
            f"Semantic resolution: {semantic_resolution.model_dump(mode='json')}\n"
            f"Schema context: {schema_text}\n"
            "Return a declarative ExecutionPlan JSON."
        )

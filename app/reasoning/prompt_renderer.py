from pathlib import Path

from app.reasoning.models import ReasoningContext


class PromptRenderer:
    """Loads markdown prompt templates and injects safe structured context."""

    def render(self, *, template_path: Path, context: ReasoningContext) -> str:
        template = template_path.read_text(encoding="utf-8")
        return template.replace("{{ context_json }}", context.model_dump_json(by_alias=True))

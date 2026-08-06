import logging
import re
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from app.compiler.models import AnalyticalHypothesis
from app.reasoning.base import BaseReasoningProvider
from app.reasoning.models import ReasoningContext, ReasoningResult
from app.reasoning.prompt_renderer import PromptRenderer

logger = logging.getLogger(__name__)

_HYPOTHESIS_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "goal": {"type": "string", "nullable": True},
        "analysis_type": {"type": "string", "nullable": True},
        "business_entity": {"type": "string", "nullable": True},
        "metric": {"type": "string", "nullable": True},
        "metrics": {"type": "array", "items": {"type": "string"}},
        "metric_source": {"type": "string", "nullable": True},
        "dimensions": {"type": "array", "items": {"type": "string"}},
        "time_scope": {"type": "string", "nullable": True},
        "filters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "field": {"type": "string", "nullable": True},
                    "operator": {"type": "string", "nullable": True},
                    "value": {},
                    "end_field": {"type": "string", "nullable": True},
                    "source": {"type": "string", "nullable": True},
                    "confidence": {"type": "number", "nullable": True},
                },
            },
        },
        "comparison_entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "nullable": True},
                    "value": {},
                    "label": {"type": "string", "nullable": True},
                    "entity_type": {"type": "string", "nullable": True},
                    "confidence": {"type": "number", "nullable": True},
                },
            },
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["confidence", "warnings"],
}


class GeminiReasoningProvider(BaseReasoningProvider):
    """Gemini-backed provider restricted to AnalyticalHypothesis generation."""

    def __init__(
        self,
        *,
        api_key: SecretStr | str | None,
        model: str = "gemini-2.5-flash",
        timeout_ms: int = 15000,
        prompt_renderer: PromptRenderer | None = None,
        client: Any | None = None,
        prompt_path: Path | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_ms = max(timeout_ms, 10000)
        self._prompt_renderer = prompt_renderer or PromptRenderer()
        self._client = client
        self._prompt_path = prompt_path or Path("app/prompts/gemini_hypothesis_prompt.md")

    def generate_hypothesis(self, context: ReasoningContext) -> ReasoningResult:
        if self._api_key is None and self._client is None:
            return ReasoningResult(
                hypothesis=None,
                raw_response=None,
                warnings=["GEMINI_API_KEY não configurada."],
                provider="gemini",
                model=self._model,
                success=False,
            )

        try:
            response_text = self._generate_text(context)
            hypothesis = AnalyticalHypothesis.model_validate_json(
                self._extract_json(response_text),
            )
        except Exception as exc:
            logger.exception(
                "Gemini hypothesis generation failed. model=%s error_type=%s",
                self._model,
                type(exc).__name__,
            )
            return ReasoningResult(
                hypothesis=None,
                raw_response=f"{type(exc).__name__}: {exc}",
                warnings=[
                    "Gemini não retornou uma AnalyticalHypothesis válida "
                    f"({type(exc).__name__}).",
                ],
                provider="gemini",
                model=self._model,
                success=False,
            )

        return ReasoningResult(
            hypothesis=hypothesis,
            raw_response=response_text,
            warnings=hypothesis.warnings,
            provider="gemini",
            model=self._model,
            success=True,
        )

    def _generate_text(self, context: ReasoningContext) -> str:
        from google.genai import types

        client = self._client or self._create_client()
        prompt = self._prompt_renderer.render(template_path=self._prompt_path, context=context)
        response = client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=_HYPOTHESIS_RESPONSE_SCHEMA,
            ),
        )
        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Gemini response text is empty.")

        return text

    def _create_client(self) -> Any:
        from google import genai
        from google.genai import types

        api_key = (
            self._api_key.get_secret_value()
            if isinstance(self._api_key, SecretStr)
            else self._api_key
        )
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=self._timeout_ms),
        )

    def _extract_json(self, text: str) -> str:
        stripped = text.strip()
        fenced_match = re.search(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL)
        if fenced_match is not None:
            return fenced_match.group(1).strip()

        return stripped


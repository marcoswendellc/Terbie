import json
import re
from pathlib import Path
from typing import Any

from pydantic import SecretStr, ValidationError

from app.compiler.models import AnalyticalHypothesis
from app.reasoning.base import BaseReasoningProvider
from app.reasoning.models import ReasoningContext, ReasoningResult
from app.reasoning.prompt_renderer import PromptRenderer


class GeminiReasoningProvider(BaseReasoningProvider):
    """Gemini-backed provider restricted to AnalyticalHypothesis generation."""

    def __init__(
        self,
        *,
        api_key: SecretStr | str | None,
        model: str = "gemini-2.5-flash",
        prompt_renderer: PromptRenderer | None = None,
        client: Any | None = None,
        prompt_path: Path | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
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
        except (
            ValidationError,
            ValueError,
            RuntimeError,
            ImportError,
            json.JSONDecodeError,
            Exception,
        ) as exc:
            return ReasoningResult(
                hypothesis=None,
                raw_response=str(exc),
                warnings=["Gemini não retornou uma AnalyticalHypothesis válida."],
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
        client = self._client or self._create_client()
        prompt = self._prompt_renderer.render(template_path=self._prompt_path, context=context)
        response = client.models.generate_content(model=self._model, contents=prompt)
        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Gemini response text is empty.")

        return text

    def _create_client(self) -> Any:
        from google import genai

        api_key = (
            self._api_key.get_secret_value()
            if isinstance(self._api_key, SecretStr)
            else self._api_key
        )
        return genai.Client(api_key=api_key)

    def _extract_json(self, text: str) -> str:
        stripped = text.strip()
        fenced_match = re.search(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL)
        if fenced_match is not None:
            return fenced_match.group(1).strip()

        return stripped

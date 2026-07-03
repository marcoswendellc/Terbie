from app.core.config import Settings
from app.reasoning.base import BaseReasoningProvider
from app.reasoning.mock_provider import MockReasoningProvider
from app.reasoning.prompt_renderer import PromptRenderer
from app.reasoning.providers.gemini_provider import GeminiReasoningProvider


class ReasoningProviderFactory:
    """Creates reasoning providers based on environment-backed settings."""

    def create(self, settings: Settings) -> BaseReasoningProvider:
        provider_name = settings.reasoning_provider.strip().lower()
        if provider_name == "gemini":
            return GeminiReasoningProvider(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                timeout_ms=settings.gemini_timeout_ms,
                prompt_renderer=PromptRenderer(),
            )

        return MockReasoningProvider()

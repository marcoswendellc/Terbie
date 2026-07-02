from app.core.config import Settings
from app.reasoning.factory import ReasoningProviderFactory
from app.reasoning.mock_provider import MockReasoningProvider
from app.reasoning.providers.gemini_provider import GeminiReasoningProvider


def test_reasoning_factory_returns_mock_by_default() -> None:
    provider = ReasoningProviderFactory().create(Settings(reasoning_provider="mock"))

    assert isinstance(provider, MockReasoningProvider)


def test_reasoning_factory_recognizes_gemini_without_calling_api() -> None:
    provider = ReasoningProviderFactory().create(
        Settings(reasoning_provider="gemini", gemini_api_key="fake-key"),
    )

    assert isinstance(provider, GeminiReasoningProvider)

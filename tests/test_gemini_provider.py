from app.reasoning.models import ReasoningContext
from app.reasoning.providers.gemini_provider import GeminiReasoningProvider
from app.semantic.resolver import SemanticResolver


class FakeGeminiResponse:
    text = """
    {
      "goal": "identificar melhores resultados",
      "analysis_type": "ranking",
      "business_entity": "restaurante",
      "metric": "faturamento",
      "time_scope": null,
      "filters": [],
      "confidence": 0.95,
      "warnings": []
    }
    """


class FakeGeminiModels:
    def generate_content(self, *, model: str, contents: str) -> FakeGeminiResponse:
        assert model == "gemini-test"
        assert "Você nunca deve responder ao usuário" in contents
        assert "DataFrame" not in contents
        return FakeGeminiResponse()


class FakeGeminiClient:
    models = FakeGeminiModels()


def test_gemini_provider_uses_mocked_sdk_call() -> None:
    question = "Quais são os 10 restaurantes com maior faturamento?"
    context = ReasoningContext(
        question=question,
        semantic_resolution=SemanticResolver().resolve(question),
    )
    provider = GeminiReasoningProvider(
        api_key="fake-key",
        model="gemini-test",
        client=FakeGeminiClient(),
    )

    result = provider.generate_hypothesis(context)

    assert result.success is True
    assert result.provider == "gemini"
    assert result.model == "gemini-test"
    assert result.hypothesis is not None
    assert result.hypothesis.metric == "faturamento"
    assert result.hypothesis.business_entity == "restaurante"

import json
from types import SimpleNamespace


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.models = self
        self.requests = []

    def generate_content(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(text=json.dumps(self.payload))


def test_gemini_decision_has_structured_output_and_timeout():
    from app.conversation.gemini import GeminiConversationProvider

    client = FakeClient(
        {
            "goal": "Campanhas",
            "assumptions": [],
            "analyses": [
                {"title": "Vendas", "question": "Compare as compras por campanha"},
            ],
        }
    )
    provider = GeminiConversationProvider(
        api_key=None, model="test", timeout_ms=15000, client=client
    )
    decision = provider.decide({"question": "Como foram as campanhas?"}, timeout_ms=5000)
    assert decision.analyses[0].question == "Compare as compras por campanha"
    config = client.requests[0]["config"]
    assert config.http_options.timeout == 5000
    assert config.response_mime_type == "application/json"


def test_gemini_invalid_decision_returns_fallback_without_retry():
    from app.conversation.gemini import GeminiConversationProvider

    client = FakeClient({"analyses": [{"question": "missing title"}]})
    provider = GeminiConversationProvider(
        api_key=None, model="test", timeout_ms=15000, client=client
    )
    assert provider.decide({}, timeout_ms=1000) is None


def test_gemini_suggestions_are_typed_and_budget_exhaustion_skips_call():
    from app.conversation.gemini import GeminiConversationProvider

    client = FakeClient(
        {
            "suggestions": [
                {
                    "label": "Público",
                    "question": "Compare os clientes",
                    "required_columns": ["sk_cliente"],
                }
            ]
        }
    )
    provider = GeminiConversationProvider(
        api_key=None, model="test", timeout_ms=15000, client=client
    )
    assert provider.suggest({}, timeout_ms=1000)[0].label == "Público"
    assert provider.suggest({}, timeout_ms=0) == []


def test_provider_without_credentials_does_not_call_external_service():
    from app.conversation.gemini import GeminiConversationProvider

    provider = GeminiConversationProvider(api_key=None, model="test", timeout_ms=15000)
    assert provider.decide({}, timeout_ms=1000) is None
    assert provider.suggest({}, timeout_ms=1000) == []

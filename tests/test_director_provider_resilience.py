import json
from contextvars import Context
from types import SimpleNamespace

import pytest

from app.conversation.gemini import GeminiConversationProvider


class Client:
    def __init__(self, response):
        self.models = self
        self.response = response
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def provider_for(response):
    client = Client(response)
    return GeminiConversationProvider(api_key=None, model="test", timeout_ms=1000, client=client), client


def test_malformed_output_is_distinguished_from_transport_failure():
    provider, client = provider_for(SimpleNamespace(text='{"analyses": [}'))
    assert provider.decide({}, timeout_ms=1000) is None
    assert provider.last_status["reason"] == "invalid_response"
    assert client.calls == 1


def test_transient_error_reports_only_safe_status_and_does_not_retry(caplog):
    class ServiceError(Exception):
        code = 503

    provider, client = provider_for(ServiceError("secret prompt and api key"))
    assert provider.decide({}, timeout_ms=1000) is None
    assert provider.last_status == {"state": "failed", "reason": "service_unavailable", "error_type": "ServiceError", "code": 503}
    assert client.calls == 1
    assert "secret prompt" not in caplog.text


def test_parsed_structured_response_is_validated_when_text_is_missing():
    provider, _ = provider_for(SimpleNamespace(text=None, parsed={"analyses": [{"title": "Vendas", "question": "Compare vendas"}]}))
    assert provider.decide({}, timeout_ms=1000).analyses[0].title == "Vendas"
    assert provider.last_status == {"state": "ok"}


def test_empty_decision_is_not_reported_as_success():
    provider, _ = provider_for(SimpleNamespace(text="{}"))
    assert provider.decide({}, timeout_ms=1000) is None
    assert provider.last_status["reason"] == "invalid_response"


def test_successful_empty_suggestions_and_budget_skip_have_distinct_status():
    provider, client = provider_for(SimpleNamespace(text=json.dumps({"suggestions": []})))
    assert provider.suggest({}, timeout_ms=1000) == []
    assert provider.last_status == {"state": "ok"}
    assert provider.suggest({}, timeout_ms=0) == []
    assert provider.last_status == {"state": "skipped", "reason": "budget_exhausted"}
    assert client.calls == 1


@pytest.mark.parametrize("code, reason", [(429, "rate_limited"), (401, "authentication"), (403, "permission_denied"), (400, "request_rejected")])
def test_http_failure_classification_does_not_guess_quota_cause(code, reason):
    error = RuntimeError("private details")
    error.code = code
    provider, _ = provider_for(error)
    assert provider.decide({}, timeout_ms=1000) is None
    assert provider.last_status["reason"] == reason


def test_timeout_and_recovery_status_do_not_leak_between_contexts():
    provider, client = provider_for(TimeoutError("private request"))
    failed_request = Context()
    assert failed_request.run(provider.decide, {}, timeout_ms=1000) is None
    assert failed_request.run(lambda: provider.last_status)["reason"] == "timeout"
    assert provider.last_status is None
    client.response = SimpleNamespace(text='{"clarification": "Qual shopping?"}')
    assert provider.decide({}, timeout_ms=1000).clarification == "Qual shopping?"
    assert provider.last_status == {"state": "ok"}
    assert failed_request.run(lambda: provider.last_status)["state"] == "failed"


def test_invalid_parsed_response_cannot_bypass_schema_validation():
    provider, _ = provider_for(SimpleNamespace(text=None, parsed={"analyses": [{"question": "missing title"}]}))
    assert provider.decide({}, timeout_ms=1000) is None
    assert provider.last_status["reason"] == "invalid_response"

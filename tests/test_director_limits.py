import pytest

from app.intent_guard import IntentGuard


@pytest.mark.parametrize("question", [
    "Qual campanha teve o maior ROI? Considere o investimento de marketing e o retorno incremental.",
    "Compare o retorno sobre o investimento das campanhas de Natal.",
    "Quanto foi o retorno incremental atribuível à promoção?",
    "Bom dia, qual o ROI?",
])
def test_roi_requests_explain_missing_inputs_without_querying_purchase_totals(question):
    result = IntentGuard().evaluate(question)
    assert result.should_stop
    assert not result.requires_data
    answer = result.response.lower()
    assert "investimento" in answer and "custos" in answer
    assert "incremental" in answer
    assert "compras registradas" in answer
    assert "não" in answer


@pytest.mark.parametrize("question", [
    "Por que a campanha de Mães 2026 do Shopping Sul vendeu mais? Foi a mídia que causou esse resultado?",
    "A publicidade causou o aumento de vendas no Natal?",
    "As vendas cresceram por causa da mídia?",
    "Qual foi o efeito causal da campanha sobre as compras?",
    "Por que as vendas da promoção cresceram?",
    "A mídia foi responsável pelo resultado da campanha?",
])
def test_causal_requests_do_not_turn_into_rankings_or_accept_unverified_growth(question):
    result = IntentGuard().evaluate(question)
    assert result.should_stop
    assert not result.requires_data
    answer = result.response.lower()
    assert "causal" in answer
    assert "compras registradas" in answer
    assert "comparação" in answer
    assert "não" in answer
    assert "ranking" not in answer


@pytest.mark.parametrize("question", [
    "Compare o faturamento de Mães 2026 e 2025 no Shopping Sul; houve mídia nas duas.",
    "Qual campanha vendeu mais?",
    "Mostre as compras registradas durante a campanha de mídia.",
    "Compare vendas antes e depois da campanha, sem atribuir causalidade.",
    "Qual o faturamento da loja Heroica?",
    "Liste os responsáveis pela campanha de mídia.",
])
def test_descriptive_comparisons_remain_supported(question):
    result = IntentGuard().evaluate(question)
    assert not result.should_stop
    assert result.requires_data

import pandas as pd
import pytest
from test_conversational_analysis import DirectorProvider
from test_recent_campaign import service

from app.conversation.models import AnalysisDecision
from app.knowledge.knowledge_service import KnowledgeService


def catalog():
    return pd.DataFrame([
        ["p1", "Mães", "Buriti Shopping", "2026-05-01", "2026-05-31"],
        ["p1", "Mães", "Buriti Shopping", "2026-05-01", "2026-05-31"],
        ["p2", "Natal", "Buriti Shopping", "2025-12-01", "2026-01-05"],
        ["p1", "Mães", "Shopping Sul", "2026-05-01", "2026-05-31"],
        ["p3", "Futura", "Buriti Shopping", "2027-01-01", "2027-01-31"],
        [None, "Sem campanha", "Buriti Shopping", "2026-01-01", "2026-12-31"],
    ], columns=["cd_promocao", "nm_promocao", "nm_empreendimento", "sk_dtinicio", "sk_dtfim"])


@pytest.mark.parametrize("question,expected", [
    ("quantas campanhas foram realizadas em 2026?", 3),
    ("Quantas promoções ocorreram em 2026 no BUR?", 2),
    ("Qual o número de campanhas em 2026?", 3),
    ("quantas campanhas foram realizadas em 2020?", 0),
])
def test_count_campaigns_uses_campaign_dates_and_unique_shopping_identity(question, expected):
    provider = DirectorProvider(AnalysisDecision(clarification="Especifique o indicador"))
    response = service(provider, catalog()).execute_question(
        question=question, knowledge_context=KnowledgeService().get_context(),
        session_id="campaign-count",
    )
    assert response.data == [{"quantidade_campanhas": expected}], response.answer
    assert str(expected) in response.answer
    assert "vigência" in response.answer
    assert "Especifique" not in response.answer


def test_campaign_count_does_not_require_receipts_revenue_or_customers():
    response = service(frame=catalog().drop(columns="nm_promocao")).execute_question(
        question="Quantas campanhas foram realizadas em 2026?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data == [{"quantidade_campanhas": 3}], response.answer


def test_campaign_count_applies_authorized_shopping_scope_before_total():
    from app.governance.policy import DataGovernancePolicy

    instance = service(frame=catalog())
    instance._governance_policy = DataGovernancePolicy(allowed_shoppings={"Buriti Shopping"})
    response = instance.execute_question(
        question="Quantas campanhas foram realizadas em 2026?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data == [{"quantidade_campanhas": 2}], response.answer

import pandas as pd
import pytest
from test_compiler_with_reasoning import SuccessfulReasoningProvider
from test_conversational_analysis import DirectorProvider
from test_recent_campaign import service

from app.conversation.models import AnalysisDecision, AnalysisQuestion
from app.knowledge.knowledge_service import KnowledgeService

NO_PELO = "No Pelo 360 com Hugo e Guilherme e Buriti Shopping"


def performance_frame():
    return pd.DataFrame([
        {
            "cd_promocao": str(index),
            "nm_promocao": campaign,
            "nm_empreendimento": shopping,
            "vl_compra": value,
            "cd_compra": str(index),
            "sk_cliente": str(index),
        }
        for index, (campaign, shopping, value) in enumerate([
            ("Natal 2025", "Buriti Shopping", 1000),
            ("Natal 2025", "Shopping Sul", 500),
            (NO_PELO, "Buriti Shopping", 10),
        ])
    ])


@pytest.mark.parametrize("question", [
    "Quais campanhas tiveram o melhor desempenho?",
    "quais campanhas tiveram a melhor performance?",
])
@pytest.mark.parametrize("with_director", [False, True])
@pytest.mark.parametrize("with_reasoning", [False, True])
def test_campaign_performance_is_global_revenue_ranking(question, with_director, with_reasoning):
    provider = DirectorProvider(AnalysisDecision(
        assumptions=["O período será a duração específica de cada campanha."],
        analyses=[AnalysisQuestion(
            title="Desempenho", question="Faturamento por campanha da campanha No Pelo 360"
        )],
    )) if with_director else None
    instance = service(provider, performance_frame())
    knowledge = KnowledgeService().get_context()
    instance.execute_question(
        question="Qual o faturamento da campanha No Pelo 360?",
        knowledge_context=knowledge, session_id="performance",
    )
    if with_reasoning:
        instance._planner_service._compiler._reasoning_provider = SuccessfulReasoningProvider()
    response = instance.execute_question(
        question=question, knowledge_context=knowledge, session_id="performance",
    )
    assert [(row["nm_promocao"], row["nm_empreendimento"], row["faturamento"])
            for row in response.data] == [
        ("Natal 2025", "Buriti Shopping", 1000),
        ("Natal 2025", "Shopping Sul", 500),
        (NO_PELO, "Buriti Shopping", 10),
    ]
    assert response.metadata.get("failed_analyses", 0) == 0
    assert "| Campanha | Shopping |" in response.answer
    assert not response.assumptions


def test_campaign_performance_preserves_requested_shopping():
    response = service(frame=performance_frame()).execute_question(
        question="Quais campanhas tiveram o melhor desempenho no Buriti Shopping?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert [row["faturamento"] for row in response.data] == [1000, 10]
    assert all(row["nm_empreendimento"] == "Buriti Shopping" for row in response.data)

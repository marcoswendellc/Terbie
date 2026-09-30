import pandas as pd
import pytest
from test_conversational_analysis import DirectorProvider
from test_recent_campaign import service

from app.conversation.models import AnalysisDecision, AnalysisQuestion
from app.knowledge.knowledge_service import KnowledgeService


@pytest.mark.parametrize(
    "metric,values",
    [
        ("faturamento", [300, 200, 100]),
        ("clientes unicos", [3, 2, 1]),
        ("quantidade de compras", [3, 2, 1]),
    ],
)
def test_campaign_performance_separates_shoppings_and_sorts_each_metric(metric, values):
    rows = campaign_rows()
    provider = DirectorProvider(
        AnalysisDecision(
            analyses=[
                AnalysisQuestion(
                    title="Desempenho por campanha", question=f"Qual o {metric} por campanha?"
                )
            ]
        )
    )
    response = service(provider, pd.DataFrame(rows)).execute_question(
        question="Quais campanhas tiveram o melhor desempenho?",
        knowledge_context=KnowledgeService().get_context(),
        session_id="campaign-ranking",
    )
    assert response.metadata.get("successful_analyses") == 1, response.answer
    assert len(response.data) == 3, response.data
    expected_shoppings = (
        ["Shopping C", "Shopping B", "Shopping A"]
        if metric == "faturamento"
        else ["Shopping B", "Shopping C", "Shopping A"]
    )
    assert [row["nm_empreendimento"] for row in response.data] == expected_shoppings
    key = {"clientes unicos": "clientes_unicos", "quantidade de compras": "quantidade_compras"}.get(
        metric, metric
    )
    assert [row[key] for row in response.data] == values
    assert "| Campanha | Shopping |" in response.answer
    assert "nm_promocao" not in response.answer


def campaign_rows():
    rows = []
    for shopping, count, amount in [
        ("Shopping A", 1, 100),
        ("Shopping B", 3, 200),
        ("Shopping C", 2, 300),
    ]:
        for index in range(count):
            rows.append(
                dict(
                    nm_promocao="Campanha Pais 2026",
                    nm_empreendimento=shopping,
                    cd_promocao=shopping,
                    cd_compra=f"{shopping}-{index}",
                    sk_cliente=f"{shopping}-{index}",
                    vl_compra=amount / count,
                    sk_dtinicio=20260701,
                    sk_dtfim=20260831,
                )
            )
    return rows


def test_comparison_keeps_same_named_campaigns_at_different_shoppings():
    response = service(frame=pd.DataFrame(campaign_rows())).execute_question(
        question="Compare o desempenho das campanhas",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert [row["nm_empreendimento"] for row in response.data] == [
        "Shopping C",
        "Shopping B",
        "Shopping A",
    ]
    for shopping in ("Shopping A", "Shopping B", "Shopping C"):
        assert shopping in response.answer


def test_single_campaign_winner_includes_its_shopping():
    response = service(frame=pd.DataFrame(campaign_rows())).execute_question(
        question="Qual campanha tem mais clientes unicos?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data[0]["nm_empreendimento"] == "Shopping B"
    assert "Shopping B" in response.answer

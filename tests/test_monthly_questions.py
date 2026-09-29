import pandas as pd
import pytest
from test_recent_campaign import service

from app.knowledge.knowledge_service import KnowledgeService


def monthly_frame():
    rows = []
    for month, count in [(1, 3), (2, 5), (8, 7)]:
        for index in range(count):
            rows.append(
                {
                    "dt_registro_mos": f"2026-{month:02d}-02 12:00:00",
                    "cd_compra": f"{month}-{index}",
                    "sk_cliente": f"c{index}",
                    "vl_compra": 100.0 * month,
                    "cd_promocao": "p1",
                    "nm_promocao": "Campanha teste",
                    "nm_empreendimento": "Shopping Sul",
                    "sk_dtinicio": 20260101,
                    "sk_dtfim": 20260831,
                }
            )
    rows.extend(
        [
            {**rows[0], "dt_registro_mos": "2025-01-01", "vl_compra": 999999},
            {**rows[0], "dt_registro_mos": "2027-01-01", "vl_compra": 999999},
            {**rows[0], "dt_registro_mos": "inválida", "vl_compra": 999999},
            {**rows[0], "cd_promocao": None, "cd_compra": "no-campaign", "vl_compra": 900},
        ]
    )
    return pd.DataFrame(rows)


@pytest.mark.parametrize(
    "question,metric,expected",
    [
        (
            "bom dia terbie, faça um gráfico evolutivo da quantidade de notas "
            "cadastradas em 2026 por mês",
            "quantidade_compras",
            [4, 5, 7],
        ),
        (
            "qual a evolução mensal do faturamento nas campanhas em 2026?",
            "faturamento",
            [300, 1000, 5600],
        ),
        ("Mostre o faturamento por mês em 2026", "faturamento", [1200, 1000, 5600]),
    ],
)
def test_monthly_questions_preserve_all_months_dates_and_scope(question, metric, expected):
    response = service(frame=monthly_frame()).execute_question(
        question=question, knowledge_context=KnowledgeService().get_context()
    )
    assert [row.get("mes") for row in response.data] == ["2026-01", "2026-02", "2026-08"]
    assert [row[metric] for row in response.data] == expected
    assert all(month in response.answer for month in ["2026-01", "2026-02", "2026-08"])
    if "gráfico" in question:
        assert response.metadata["chart"]["x"] == "mes"
        assert response.metadata["chart"]["y"] == metric


def test_monthly_then_campaign_ranking_does_not_inherit_previous_scope():
    instance = service(frame=monthly_frame())
    instance.execute_question(
        question="Faturamento por mês em 2025",
        knowledge_context=KnowledgeService().get_context(),
        session_id="sequence",
    )
    response = instance.execute_question(
        question="qual campanha apresentou maior faturamento em 2026?",
        knowledge_context=KnowledgeService().get_context(),
        session_id="sequence",
    )
    assert response.data[0]["nm_promocao"] == "Campanha teste"
    assert "mes" not in response.data[0]


def test_director_cannot_turn_monthly_request_into_january_only():
    from test_conversational_analysis import DirectorProvider

    from app.conversation.models import AnalysisDecision, AnalysisQuestion

    provider = DirectorProvider(
        AnalysisDecision(
            analyses=[
                AnalysisQuestion(
                    title="Janeiro", question="Qual a quantidade de compras em janeiro de 2026?"
                )
            ]
        )
    )
    response = service(provider, monthly_frame()).execute_question(
        question="Quantidade de notas por mês em 2026",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert [row.get("mes") for row in response.data] == ["2026-01", "2026-02", "2026-08"]


def test_monthly_keeps_second_grouping_dimension():
    frame = monthly_frame()
    frame["nm_segmento"] = ["Moda" if i % 2 else "Alimentação" for i in range(len(frame))]
    response = service(frame=frame).execute_question(
        question="Faturamento por mês e por segmento em 2026",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert len(response.data) == 6
    assert all("nm_segmento" in row and "mes" in row for row in response.data)
    assert "chart" not in response.metadata  # A single line cannot represent multiple segments.


def test_monthly_respects_named_month_interval():
    response = service(frame=monthly_frame()).execute_question(
        question="Faturamento mensal de fevereiro a agosto de 2026",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert [row.get("mes") for row in response.data] == ["2026-02", "2026-08"]

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


@pytest.mark.parametrize("question", [
    "Qual foi o total de vendas por mês?",
    "qual foi o mês de maior faturamento ?",
])
def test_monthly_sales_cannot_be_redirected_to_a_campaign(question):
    from test_conversational_analysis import DirectorProvider

    from app.conversation.models import AnalysisDecision, AnalysisQuestion

    provider = DirectorProvider(AnalysisDecision(analyses=[AnalysisQuestion(
        title="Campanha", question="Faturamento por mês da campanha No Pelo 360"
    )]))
    instance = service(provider, monthly_frame())
    response = instance.execute_question(
        question=question, knowledge_context=KnowledgeService().get_context(),
        session_id="monthly-sales",
    )
    if "maior" in question:
        assert response.data == [{"mes": "2025-01", "faturamento": 999999.0}]
        assert "mês" in response.answer.lower()
        assert "evolução mensal" not in response.answer.lower()
    else:
        assert [row["mes"] for row in response.data] == [
            "2025-01", "2026-01", "2026-02", "2026-08", "2027-01"
        ]
        assert sum(row["faturamento"] for row in response.data) == 2007798
    assert not any("No Pelo" in str(row) for row in response.data)


def test_monthly_sales_sequence_keeps_global_scope():
    instance = service(frame=monthly_frame())
    knowledge = KnowledgeService().get_context()
    answers = []
    for question in [
        "Qual foi o total de vendas por mês?",
        "Quais campanhas tiveram o melhor desempenho?",
        "qual foi o mês de maior faturamento ?",
        "Qual foi o total de vendas por mês?",
    ]:
        answers.append(instance.execute_question(
            question=question, knowledge_context=knowledge, session_id="sequence-sales"
        ))
    assert answers[0].data == answers[-1].data
    assert answers[2].data == [{"mes": "2025-01", "faturamento": 999999.0}]


def test_highest_month_preserves_explicit_year():
    response = service(frame=monthly_frame()).execute_question(
        question="Qual foi o mês de maior faturamento em 2026?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data == [{"mes": "2026-08", "faturamento": 5600.0}]


@pytest.mark.parametrize("question", [
    "Qual foi o mês de maior faturamento entre fevereiro e agosto de 2026?",
    "Qual foi o mês de maior faturamento nas campanhas em 2026?",
])
def test_highest_month_preserves_requested_purchase_scope(question):
    frame = monthly_frame()
    frame.loc[frame.cd_promocao.isna(), "vl_compra"] = 100000
    response = service(frame=frame).execute_question(
        question=question, knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data == [{"mes": "2026-08", "faturamento": 5600.0}]


def test_highest_month_preserves_explicit_purchase_count():
    response = service(frame=monthly_frame()).execute_question(
        question="Qual foi o mês com maior quantidade de vendas em 2026?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data == [{"mes": "2026-08", "quantidade_compras": 7}]


@pytest.mark.parametrize("metric", ["vendas", "faturamento"])
def test_explicit_monthly_query_drops_previous_campaign_but_keeps_requested_campaign(metric):
    frame = monthly_frame()
    frame["nm_promocao"] = "No Pelo 360 com Hugo e Guilherme e Buriti Shopping"
    other = frame.iloc[[0]].copy()
    other["nm_promocao"] = "Outra campanha"
    other["vl_compra"] = 50000
    frame = pd.concat([frame, other], ignore_index=True)
    instance = service(frame=frame)
    knowledge = KnowledgeService().get_context()
    scoped = instance.execute_question(
        question=f"Total de {metric} por mês da campanha No Pelo 360 em 2026",
        knowledge_context=knowledge, session_id="campaign-scope",
    )
    assert sum(row["faturamento"] for row in scoped.data) == 6900
    global_result = instance.execute_question(
        question=f"Total de {metric} por mês em 2026",
        knowledge_context=knowledge, session_id="campaign-scope",
    )
    assert sum(row["faturamento"] for row in global_result.data) == 57800

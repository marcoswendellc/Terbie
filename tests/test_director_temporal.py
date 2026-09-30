from test_campaign_year_conversation import campaign_frame
from test_recent_campaign import service

from app.knowledge.knowledge_service import KnowledgeService


def ask(question, frame=None):
    return service(frame=frame).execute_question(
        question=question, knowledge_context=KnowledgeService().get_context(),
        session_id="director-temporal",
    )


def test_recent_campaign_identifies_shopping_without_requesting_filter():
    response = ask("Qual foi a campanha mais recente e em qual shopping aconteceu?")
    assert response.data[0]["nm_promocao"] == "Recente"
    assert "Shopping B" in response.answer


def test_missing_comparison_side_preserves_available_campaign():
    response = ask(
        "Compare a campanha de pais 2025 do Buriti Shopping com a campanha de mães 2025 do Buriti Shopping.",
        campaign_frame(),
    )
    assert len(response.data) == 2
    assert response.data[0]["faturamento"] == 100
    assert response.data[1]["faturamento"] is None
    assert "Sem dados" in response.answer
    assert "2025" in response.answer
    assert "Variação percentual" not in response.answer


def test_shared_year_missing_side_does_not_use_another_year():
    frame = campaign_frame()
    frame.loc[1, "nm_promocao"] = "Promoção Mães 2026"
    response = ask(
        "Compare a campanha de pais com a campanha de mães do Buriti Shopping em 2025.",
        frame,
    )
    assert len(response.data) == 2
    assert response.data[0]["faturamento"] == 100
    assert response.data[1]["faturamento"] is None
    assert "2026" not in response.answer


def test_listing_de_year_followup_preserves_shopping():
    instance = service(frame=campaign_frame())
    context = KnowledgeService().get_context()
    instance.execute_question(
        question="Liste as campanhas de 2025 no Buriti Shopping",
        knowledge_context=context, session_id="listing-de-year",
    )
    response = instance.execute_question(
        question="E em 2026?", knowledge_context=context, session_id="listing-de-year",
    )
    assert len(response.data) == 1
    assert response.data[0]["nm_empreendimento"] == "Buriti Shopping"
    assert "2026" in response.data[0]["nm_promocao"]


def test_different_campaign_events_and_durations_are_explicit():
    frame = campaign_frame().iloc[1:].copy()
    frame.loc[1, ["nm_promocao", "sk_dtinicio", "sk_dtfim"]] = [
        "Promoção Mães e Namorados 2026", 20260420, 20260612,
    ]
    frame.loc[2, ["nm_promocao", "sk_dtinicio", "sk_dtfim"]] = [
        "Promoção Mães 2026", 20260425, 20260510,
    ]
    response = ask(
        "Compare a campanha de mães 2026 do Buriti Shopping com a campanha de mães 2026 do Shopping Sul.",
        frame,
    )
    assert [row["faturamento"] for row in response.data] == [250, 999]
    assert "20/04/2026" in response.answer
    assert "10/05/2026" in response.answer
    assert "eventos" in response.answer.lower()
    assert "durações" in response.answer.lower()

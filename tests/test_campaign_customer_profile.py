import pandas as pd
import pytest
from test_conversational_analysis import DirectorProvider
from test_recent_campaign import service

from app.conversation.models import AnalysisDecision, AnalysisQuestion
from app.knowledge.knowledge_service import KnowledgeService

NO_PELO = "No Pelo 360 com Hugo e Guilherme e Buriti Shopping"
MOTHERS = "Promoção Mães E Namorados 2026"


def profile_frame():
    rows = []
    for campaign, shopping, count, sex, amount in [
        (MOTHERS, "Buriti Shopping", 3, "F", 100),
        (NO_PELO, "Buriti Shopping", 2, "M", 200),
        (MOTHERS, "Shopping Sul", 5, "M", 1000),
        ("Promoção Mães 2025", "Buriti Shopping", 4, "M", 500),
    ]:
        for index in range(count):
            rows.append({
                "nm_promocao": campaign, "nm_empreendimento": shopping,
                "cd_promocao": campaign + shopping,
                "cd_compra": f"{campaign}-{shopping}-{index}",
                "sk_cliente": f"{campaign}-{shopping}-{index}",
                "cd_sexo": sex, "dt_nascimento": "1990-01-01",
                "vl_compra": amount, "cidade": "Goiânia",
                "sk_dtinicio": 20250101 if "2025" in campaign else 20260101,
                "sk_dtfim": 20251231 if "2025" in campaign else 20261231,
            })
    return pd.DataFrame(rows)


@pytest.mark.parametrize("question", [
    "qual perfil dos clientes que visitaram o buriti shopping na promoção mães 2026?",
    "Qual o perfil dos clientes da campanha mães 2026 no Buriti Shopping?",
])
@pytest.mark.parametrize("with_director", [False, True])
def test_profile_uses_requested_campaign_and_shopping(question, with_director):
    provider = DirectorProvider(AnalysisDecision(analyses=[AnalysisQuestion(
        title="Perfil incorreto", question="Perfil dos clientes da campanha No Pelo 360",
    )])) if with_director else None
    instance = service(provider, profile_frame())
    knowledge = KnowledgeService().get_context()
    instance.execute_question(
        question="Qual o faturamento da campanha No Pelo 360?",
        knowledge_context=knowledge, session_id="profile",
    )
    result = instance.execute_question(
        question=question, knowledge_context=knowledge, session_id="profile",
    )
    assert result.data, result.answer
    assert result.data[0]["clientes_unicos"] == 3
    assert result.data[0]["quantidade_compras"] == 3
    assert result.data[0]["faturamento"] == 300
    assert result.data[0]["genero_predominante"] == "Feminino"
    assert MOTHERS in result.answer
    assert NO_PELO not in result.answer


def test_profile_does_not_substitute_an_unavailable_campaign_year():
    result = service(frame=profile_frame()).execute_question(
        question="Qual perfil dos clientes do Buriti Shopping na promoção mães 2027?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert result.data == []


def test_profile_does_not_substitute_an_unavailable_campaign_event():
    result = service(frame=profile_frame()).execute_question(
        question="Qual perfil dos clientes do Buriti Shopping na promoção festas 2026?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert result.data == []


def test_profile_does_not_arbitrarily_choose_between_two_partial_campaign_matches():
    frame = profile_frame()
    extra = frame.iloc[[0]].copy()
    extra["nm_promocao"] = "Promoção Mães Premiada 2026"
    result = service(frame=pd.concat([frame, extra], ignore_index=True)).execute_question(
        question="Qual perfil dos clientes do Buriti Shopping na promoção mães 2026?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert result.data == []


def test_profile_accepts_unique_short_campaign_name_without_a_year():
    frame = profile_frame()
    frame = frame[~frame.nm_promocao.str.contains("2025")]
    result = service(frame=frame).execute_question(
        question="Qual perfil dos clientes do Buriti Shopping na promoção mães?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert result.data, result.answer
    assert result.data[0]["clientes_unicos"] == 3
    assert MOTHERS in result.answer

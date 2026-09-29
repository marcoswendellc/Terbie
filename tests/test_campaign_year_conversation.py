import pandas as pd
import pytest
from test_comparative_analytics import _compile
from test_conversational_analysis import DirectorProvider
from test_recent_campaign import service

from app.conversation.models import AnalysisDecision, AnalysisQuestion
from app.executor.context import ExecutionContext
from app.executor.operations.campaign_context_comparison import CampaignContextComparisonOperation
from app.knowledge.knowledge_service import KnowledgeService
from app.planner.models import PlanOperation
from app.semantic.temporal import resolve_temporal_reference

QUESTION = "compare a campanha de pais de 2025 com a campanha de pais de 2026 do buriti shopping"


def campaign_frame():
    return pd.DataFrame(
        [
            dict(
                cd_promocao=str(index),
                nm_promocao=f"Promoção Pais {year}",
                nm_empreendimento=shopping,
                sk_dtinicio=int(f"{year}0701"),
                sk_dtfim=int(f"{year}0831"),
                vl_compra=value,
                cd_compra=str(index),
                sk_cliente=str(index),
            )
            for index, (year, shopping, value) in enumerate(
                [
                    (2025, "Buriti Shopping", 100),
                    (2026, "Buriti Shopping", 250),
                    (2026, "Shopping Sul", 999),
                ]
            )
        ]
    )


def test_cross_year_comparison_has_no_global_first_year_filter():
    response = _compile(QUESTION)
    assert not any(
        op.parameters.get("operator") == "year_overlap" for op in response.execution_plan.operations
    )


def test_shared_year_scope_is_preserved_when_campaign_names_have_no_year():
    frame = campaign_frame()
    frame.loc[1, "nm_promocao"] = "Promoção Mães 2026"
    frame.loc[2, ["nm_promocao", "nm_empreendimento", "sk_dtinicio", "sk_dtfim"]] = [
        "Promoção Mães 2025", "Buriti Shopping", 20250701, 20250831
    ]
    response = service(frame=frame).execute_question(
        question="compare a campanha de pais com a campanha de mães do buriti shopping em 2025",
        knowledge_context=KnowledgeService().get_context(), session_id="shared-year"
    )
    assert [row["faturamento"] for row in response.data] == [100, 999]


def test_year_followup_accepts_listing_with_de_year():
    assert resolve_temporal_reference(
        "e em 2026?", "Liste as campanhas de 2025 no Buriti Shopping"
    ) == "Liste as campanhas de 2026 no Buriti Shopping"


def test_missing_requested_year_does_not_match_another_year():
    operation = PlanOperation(
        type="campaign_context_comparison",
        parameters={
            "contexts": [
                {"promotion": f"pais de {year}", "shopping": "Buriti Shopping"}
                for year in (2025, 2027)
            ]
        },
    )
    context = ExecutionContext(knowledge_context=KnowledgeService().get_context())
    result = CampaignContextComparisonOperation().execute(campaign_frame(), operation, context)
    assert result.iloc[0]["faturamento"] == 100
    assert pd.isna(result.iloc[1]["faturamento"])
    assert "2027" in result.iloc[1]["campanha_contexto"]


@pytest.mark.parametrize("with_director", [False, True])
def test_listing_year_followup_and_cross_year_comparison(with_director):
    provider = (
        DirectorProvider(
            AnalysisDecision(
                analyses=[
                    AnalysisQuestion(
                        title="Wrong rewrite",
                        question="Qual campanha teve maior faturamento em 2025?",
                    )
                ]
            )
        )
        if with_director
        else None
    )
    instance = service(provider, campaign_frame())

    def ask(question):
        return instance.execute_question(
            question=question,
            session_id="campaign-years",
            knowledge_context=KnowledgeService().get_context(),
        )

    first = ask("olá terbie, quais campanhas ocorreram em 2025?")
    assert len(first.data) == 1
    assert "| Campanha | Shopping | Início | Fim |" in first.answer
    assert "| Buriti Shopping |" in first.answer
    second = ask("e em 2026 ?")
    assert len(second.data) == 2
    assert {row["nm_promocao"] for row in second.data} == {"Promoção Pais 2026"}
    third = ask(QUESTION)
    assert [row["faturamento"] for row in third.data] == [100, 250]
    assert "Promoção Pais 2025 — Buriti Shopping" in third.answer
    assert "Promoção Pais 2026 — Buriti Shopping" in third.answer
    assert "150,00%" in third.answer


def test_year_followup_preserves_listing_shopping_and_does_not_rewrite_campaign_name():
    assert (
        resolve_temporal_reference(
            "e em 2026?", "Quais campanhas ocorreram em 2025 no Buriti Shopping?"
        )
        == "Quais campanhas ocorreram em 2026 no Buriti Shopping?"
    )
    assert (
        resolve_temporal_reference("e em 2026?", "Qual o faturamento da Promoção Pais 2025?")
        is None
    )


def test_verifier_rejects_two_sides_resolved_to_the_same_campaign():
    from app.executor.models import ExecutionResult
    from app.services.analysis_verifier import AnalysisVerifier

    plan = _compile(QUESTION).execution_plan.model_copy(
        update={
            "operations": [
                PlanOperation(
                    type="campaign_context_comparison",
                    parameters={
                        "contexts": [
                            {"promotion": "pais 2025", "shopping": "Buriti Shopping"},
                            {"promotion": "pais 2026", "shopping": "Buriti Shopping"},
                        ]
                    },
                )
            ]
        }
    )
    result = ExecutionResult(
        data=[
            {"campanha_contexto": "Promoção Pais 2025 — Buriti Shopping", "faturamento": 100},
            {"campanha_contexto": "Promoção Pais 2025 — Buriti Shopping", "faturamento": 100},
        ],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=2,
    )
    assert not AnalysisVerifier().verify(plan=plan, result=result).passed

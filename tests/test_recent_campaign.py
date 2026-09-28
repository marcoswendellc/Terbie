import pandas as pd
import pytest
from test_conversational_analysis import DirectorProvider, _execution_service
from test_multi_query_flow import _compiler, _executor

from app.compiler.models import AnalyticalHypothesis
from app.knowledge.knowledge_service import KnowledgeService
from app.planner.models import ExecutionPlan, PlanMetric, PlanOperation
from app.reasoning.models import ReasoningResult


def campaign_data():
    return pd.DataFrame(
        [
            {
                "cd_promocao": "old",
                "nm_promocao": "Antiga e rica",
                "nm_empreendimento": "Shopping A",
                "sk_dtinicio": 20200101,
                "sk_dtfim": "31/12/2023",
                "vl_compra": 999999,
                "sk_cliente": "cliente1",
                "cd_compra": "compra1",
                "bairro": "NULL",
            },
            {
                "cd_promocao": "new",
                "nm_promocao": "Recente",
                "nm_empreendimento": "Shopping B",
                "sk_dtinicio": "2022-08-01",
                "sk_dtfim": "2022-09-01",
                "vl_compra": 10,
                "sk_cliente": "cliente2",
                "cd_compra": "compra2",
                "bairro": "NULL",
            },
            {
                "cd_promocao": "new",
                "nm_promocao": "Recente",
                "nm_empreendimento": "Shopping B",
                "sk_dtinicio": "2022-08-01",
                "sk_dtfim": "2022-09-01",
                "vl_compra": 20,
                "sk_cliente": "cliente3",
                "cd_compra": "compra3",
                "bairro": "NULL",
            },
            {
                "cd_promocao": "future",
                "nm_promocao": "Futura",
                "nm_empreendimento": "Shopping B",
                "sk_dtinicio": "2099-01-01",
                "sk_dtfim": "2099-02-01",
                "vl_compra": 500,
                "sk_cliente": "cliente4",
                "cd_compra": "compra4",
                "bairro": "NULL",
            },
        ]
    )


class LocalData:
    def __init__(self, frame=None):
        self.frame = frame if frame is not None else campaign_data()

    def read_google_spreadsheet_data(self, **kwargs):
        return {"Dados_copiloto": self.frame.copy()}


def service(provider=None, frame=None):
    instance = _execution_service(provider)
    instance._data_service = LocalData(frame)
    return instance


@pytest.mark.parametrize(
    "question,expected",
    [
        ("Olá terbie, bom dia! Qual a campanha mais recente?", "Recente"),
        ("Qual a última campanha?", "Recente"),
        ("Qual a campanha encerrada mais recentemente?", "Antiga e rica"),
        ("Qual a campanha mais antiga?", "Antiga e rica"),
    ],
)
def test_temporal_lookup_uses_dates_not_revenue(question, expected):
    response = service().execute_question(
        question=question, knowledge_context=KnowledgeService().get_context(), session_id="one"
    )
    assert [row["nm_promocao"] for row in response.data] == [expected]
    assert "cd_compra" not in str(response.data)
    assert "faturamento" not in response.answer.lower()
    assert "Shopping" in response.answer
    assert "202" in response.answer


def test_bad_director_cannot_replace_recency_with_revenue_or_raw_rows():
    from app.conversation.models import AnalysisDecision, AnalysisQuestion

    provider = DirectorProvider(
        AnalysisDecision(
            assumptions=["Ordenei pelo faturamento."],
            analyses=[
                AnalysisQuestion(title="Ranking", question="As 10 campanhas com maior faturamento")
            ],
        )
    )
    instance = service(provider)
    knowledge = KnowledgeService().get_context()
    first = instance.execute_question(
        question="Olá terbie, bom dia! Qual a campanha mais recente?",
        knowledge_context=knowledge,
        session_id="one",
    )
    second = instance.execute_question(
        question="qual foi a mais recente?", knowledge_context=knowledge, session_id="one"
    )
    assert [row["nm_promocao"] for row in first.data] == ["Recente"]
    assert [row["nm_promocao"] for row in second.data] == ["Recente"]
    assert first.assumptions and "início" in first.assumptions[0]
    assert "faturamento" not in second.answer.lower()


def test_invalid_aggregation_never_returns_purchase_rows():
    from app.core.exceptions import ServiceError

    plan = ExecutionPlan(
        intent="ranking",
        metrics=[PlanMetric(name="bairro")],
        operations=[
            PlanOperation(type="aggregate", function=None, field=None),
            PlanOperation(type="sort", field="bairro"),
            PlanOperation(type="limit", parameters={"value": None}),
        ],
    )
    with pytest.raises(ServiceError):
        _executor().execute(
            dataframe=campaign_data(), plan=plan, knowledge_context=KnowledgeService().get_context()
        )


@pytest.mark.parametrize(
    "operation",
    [
        PlanOperation(type="aggregate", parameters={"metrics": []}),
        PlanOperation(type="select", parameters={"fields": []}),
        PlanOperation(type="select", parameters={"fields": ["inexistente"]}),
        PlanOperation(type="unsupported"),
    ],
)
def test_invalid_operation_fails_closed(operation):
    from app.core.exceptions import ServiceError

    with pytest.raises(ServiceError):
        _executor().execute(
            dataframe=campaign_data(),
            plan=ExecutionPlan(operations=[operation]),
            knowledge_context=KnowledgeService().get_context(),
        )


def test_compiler_does_not_accept_llm_revenue_plan_for_date_question():
    from app.compiler.models import CompilerRequest
    from app.semantic.resolver import SemanticResolver

    class BadReasoning:
        def generate_hypothesis(self, context):
            return ReasoningResult(
                provider="test",
                success=True,
                hypothesis=AnalyticalHypothesis(
                    analysis_type="ranking", business_entity="promocao", metric="faturamento"
                ),
            )

    compiler = _compiler()
    compiler._reasoning_provider = BadReasoning()
    question = "Qual a campanha mais recente?"
    result = compiler.compile(
        CompilerRequest(
            question=question,
            semantic_resolution=SemanticResolver().resolve(question),
            knowledge_context=KnowledgeService().get_context(),
        )
    )
    assert not result.execution_plan.metrics
    assert any(
        op.type == "sort" and op.field == "sk_dtinicio" for op in result.execution_plan.operations
    )
    assert any(
        op.type == "limit" and op.parameters["value"] == 1
        for op in result.execution_plan.operations
    )


def test_repeated_correction_keeps_campaign_scope_and_allows_changing_order():
    instance = service(DirectorProvider(None))
    knowledge = KnowledgeService().get_context()
    for question in [
        "Qual a campanha mais recente?",
        "Qual foi a mais recente?",
        "Qual foi a mais recente?",
    ]:
        response = instance.execute_question(
            question=question, knowledge_context=knowledge, session_id="s"
        )
        assert response.data[0]["nm_promocao"] == "Recente"
    oldest = instance.execute_question(
        question="Qual foi a mais antiga?", knowledge_context=knowledge, session_id="s"
    )
    assert oldest.data[0]["nm_promocao"] == "Antiga e rica"


def test_temporal_lookup_preserves_requested_shopping():
    frame = campaign_data().replace({"Shopping A": "Buriti Shopping", "Shopping B": "Shopping Sul"})
    response = service(frame=frame).execute_question(
        question="Qual a campanha mais recente do Buriti Shopping?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert [row["nm_promocao"] for row in response.data] == ["Antiga e rica"]


def test_equal_dates_are_reported_as_a_tie_not_arbitrary_winner():
    frame = campaign_data()
    row = frame.iloc[1].copy()
    row["nm_promocao"] = "Outra recente"
    row["nm_empreendimento"] = "Shopping C"
    frame = pd.concat([frame, pd.DataFrame([row])], ignore_index=True)
    response = service(frame=frame).execute_question(
        question="Qual a campanha mais recente?", knowledge_context=KnowledgeService().get_context()
    )
    assert {row["nm_promocao"] for row in response.data} == {"Recente", "Outra recente"}
    assert "empate" in response.answer


def test_missing_valid_dates_returns_no_purchase_data():
    frame = campaign_data()
    frame["sk_dtinicio"] = "NULL"
    response = service(frame=frame).execute_question(
        question="Qual a campanha mais recente?", knowledge_context=KnowledgeService().get_context()
    )
    assert response.data == []
    assert "cd_compra" not in response.answer


def test_invalid_plan_is_explained_without_calling_narrator():
    from types import SimpleNamespace

    class InvalidPlanner:
        def create_draft_plan(self, **kwargs):
            return SimpleNamespace(plan=ExecutionPlan(operations=[PlanOperation(type="aggregate")]))

    class ForbiddenNarrator:
        def narrate(self, request):
            pytest.fail("Invalid output reached narrator")

    instance = service()
    instance._planner_service = InvalidPlanner()
    instance._narrator_service = ForbiddenNarrator()
    response = instance.execute_question(
        question="Qual foi a mais recente?", knowledge_context=KnowledgeService().get_context()
    )
    assert response.data == []
    assert response.metadata["response_type"] == "analysis_failed"


@pytest.mark.parametrize(
    "question",
    [
        "Qual a campanha mais recente antes de 2022?",
        "Qual a campanha mais recente do Shopping Desconhecido?",
    ],
)
def test_unresolved_scope_clarifies_instead_of_answering_broader_question(question):
    response = service().execute_question(
        question=question, knowledge_context=KnowledgeService().get_context()
    )
    assert response.data == []
    assert response.metadata["response_type"] == "clarification_required"


def test_ended_in_year_filters_ending_date_not_campaign_overlap():
    response = service().execute_question(
        question="Qual a campanha mais recente encerrada em 2022?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert [row["nm_promocao"] for row in response.data] == ["Recente"]


def test_active_campaign_excludes_ended_campaigns():
    response = service().execute_question(
        question="Qual a campanha mais recente que ainda está ativa?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data == []


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2022-08-01T00:00:00Z", "2022-08-01"),
        ("2022-08-01T00:00:00+03:00", "2022-08-01"),
        (44927.5, "2023-01-01"),
    ],
)
def test_calendar_dates_support_iso_timezone_and_fractional_excel_serial(value, expected):
    from app.executor.dates import date_series

    assert date_series(pd.Series([value])).dt.strftime("%Y-%m-%d").iloc[0] == expected


@pytest.mark.parametrize(
    "question",
    [
        "Quando foi a primeira venda da campanha Arca Parque?",
        "Qual a compra mais recente da campanha Arca Parque?",
        "Qual o faturamento da campanha mais recente?",
    ],
)
def test_campaign_chronology_does_not_override_other_analytical_targets(question):
    from app.semantic.temporal import TemporalSelection

    assert TemporalSelection.parse(question) is None

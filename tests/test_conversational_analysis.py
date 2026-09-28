import pandas as pd
import pytest

from app.memory.conversation import ConversationMemoryService
from app.memory.in_memory import InMemorySessionStore
from app.memory.models import ContextualQuestion
from app.narrator.models import ExecuteResponse


def _suggestion():
    from app.conversation.models import FollowUpSuggestion

    return FollowUpSuggestion(
        label="Perfil do público",
        question="Qual o perfil etário dos clientes da campanha Mães 2026 no Buriti Shopping?",
        required_columns=["sk_cliente", "dt_nascimento"],
    )


def _save(memory, session="one", suggestions=None):
    context = ContextualQuestion(
        original_question="Compare as campanhas",
        rewritten_question="Compare as campanhas",
        summary="",
        state=memory.get(session).state,
    )
    memory.record(
        session_id=session,
        context=context,
        answer="Resultado calculado.",
        suggestions=suggestions if suggestions is not None else [_suggestion()],
        analysis_questions=["Compare as campanhas do Buriti Shopping"],
        goal="Comparar campanhas",
    )


@pytest.mark.parametrize("choice", ["o perfil", "Perfil do público", "a primeira", "1"])
def test_suggestion_selection_resolves_complete_question(choice):
    memory = ConversationMemoryService(InMemorySessionStore())
    _save(memory)
    result = memory.contextualize(session_id="one", question=choice)
    assert result.rewritten_question == _suggestion().question
    assert result.original_question == choice
    assert result.clarification is None


def test_suggestions_are_isolated_and_explicit_redirection_is_not_swallowed():
    memory = ConversationMemoryService(InMemorySessionStore())
    _save(memory)
    assert memory.get("other").suggestions == []
    redirected = memory.contextualize(session_id="one", question="Perfil no Shopping Sul")
    assert redirected.rewritten_question != _suggestion().question
    assert "Buriti" not in redirected.rewritten_question


def test_ambiguous_acceptance_requests_choice():
    memory = ConversationMemoryService(InMemorySessionStore())
    other = _suggestion().model_copy(update={"label": "Consumo por cliente"})
    _save(memory, suggestions=[_suggestion(), other])
    assert memory.contextualize(session_id="one", question="sim").clarification


def test_sqlite_persists_suggestions_and_new_turn_clears_old_ones(tmp_path):
    from app.memory.sqlite import SQLiteSessionStore

    memory = ConversationMemoryService(SQLiteSessionStore(str(tmp_path / "memory.db")))
    _save(memory)
    assert memory.get("one").suggestions == [_suggestion()]
    assert memory.get("one").analysis_questions == ["Compare as campanhas do Buriti Shopping"]
    _save(memory, suggestions=[])
    assert memory.get("one").suggestions == []


class DirectorProvider:
    def __init__(self, decision, suggestions=None):
        self.decision = decision
        self.suggestions = suggestions or []
        self.contexts = []

    def decide(self, context, *, timeout_ms):
        self.contexts.append(context)
        return self.decision

    def suggest(self, context, *, timeout_ms):
        self.contexts.append(context)
        return self.suggestions


def test_director_executes_only_requested_analyses_and_validates_suggestions():
    from app.conversation.director import ConversationDirector
    from app.conversation.models import AnalysisDecision, AnalysisQuestion

    provider = DirectorProvider(
        AnalysisDecision(
            goal="Comparar campanhas",
            assumptions=["Considero as compras registradas."],
            analyses=[AnalysisQuestion(title="Vendas", question="Some as compras")],
        ),
        [
            _suggestion(),
            _suggestion().model_copy(
                update={
                    "label": "Fluxo",
                    "required_columns": ["fluxo_visitantes"],
                }
            ),
        ],
    )
    executed = []

    def execute(question):
        executed.append(question)
        return ExecuteResponse(question=question, answer="R$ 300", data=[{"faturamento": 300}])

    response = ConversationDirector(provider).run(
        question="Como foram as campanhas?",
        session=None,
        schemas={"compras": {"vl_compra": "float", "sk_cliente": "str", "dt_nascimento": "date"}},
        knowledge={},
        execute=execute,
    )
    assert executed == ["Some as compras"]
    assert response.data == [{"faturamento": 300}]
    assert response.suggestions == [_suggestion()]
    assert "compras registradas" in response.assumptions[0]


def test_director_clarifies_without_executing():
    from app.conversation.director import ConversationDirector
    from app.conversation.models import AnalysisDecision

    provider = DirectorProvider(AnalysisDecision(clarification="Qual shopping?"))
    response = ConversationDirector(provider).run(
        question="E naquele?",
        session=None,
        schemas={},
        knowledge={},
        execute=lambda _: pytest.fail("Clarification must not execute queries"),
    )
    assert response.answer == "Qual shopping?"
    assert response.metadata["response_type"] == "clarification_required"


def test_director_keeps_partial_results_and_limits_queries():
    from app.conversation.director import ConversationDirector
    from app.conversation.models import AnalysisDecision, AnalysisQuestion

    provider = DirectorProvider(
        AnalysisDecision(
            analyses=[
                AnalysisQuestion(title="Vendas", question="vendas"),
                AnalysisQuestion(title="Perfil", question="perfil"),
                AnalysisQuestion(title="Lojas", question="lojas"),
            ]
        )
    )
    called = []

    def execute(question):
        called.append(question)
        if question == "perfil":
            raise ValueError("Internal data error")
        return ExecuteResponse(question=question, answer="Calculado", data=[{"total": 100}])

    result = ConversationDirector(provider, max_analyses=2).run(
        question="Analise",
        session=None,
        schemas={},
        knowledge={},
        execute=execute,
    )
    assert called == ["vendas", "perfil"]
    assert result.metadata["successful_analyses"] == 1
    assert result.metadata["failed_analyses"] == 1
    assert "Internal data error" not in result.answer
    assert result.warnings


def test_provider_receives_schema_without_source_rows():
    from app.conversation.director import schema_context

    frame = pd.DataFrame([{"vl_compra": 999, "email": "private@example.com"}])
    context = schema_context({"compras": frame})
    assert context["compras"]["vl_compra"] == "int64"
    assert "999" not in str(context)
    assert "private@example.com" not in str(context)


def _execution_service(provider=None, narrator=None):
    from test_multi_query_flow import MultiQueryDataService, _compiler, _executor

    from app.conversation.director import ConversationDirector
    from app.core.config import Settings
    from app.narrator.context_builder import NarrativeContextBuilder
    from app.narrator.formatter import NarrativeFormatter
    from app.narrator.narrator import TerbieNarrator
    from app.semantic.resolver import SemanticResolver
    from app.services.execution_service import ExecutionService
    from app.services.narrator_service import NarratorService
    from app.services.planner_service import PlannerService
    from app.services.semantic_service import SemanticService

    return ExecutionService(
        settings=Settings(_env_file=None, google_sheets_spreadsheet_id="test"),
        semantic_service=SemanticService(resolver=SemanticResolver()),
        planner_service=PlannerService(compiler=_compiler()),
        data_service=MultiQueryDataService(),
        executor=_executor(),
        narrator_service=narrator
        or NarratorService(
            narrator=TerbieNarrator(
                context_builder=NarrativeContextBuilder(),
                formatter=NarrativeFormatter(),
            )
        ),
        conversation_memory=ConversationMemoryService(InMemorySessionStore()),
        conversation_director=ConversationDirector(provider) if provider else None,
    )


def test_full_conversation_executes_selected_suggestion_and_keeps_numeric_results():
    from app.conversation.models import AnalysisDecision, AnalysisQuestion, FollowUpSuggestion
    from app.knowledge.knowledge_service import KnowledgeService

    question = "Qual o faturamento da campanha Arca Parque?"
    next_question = "Qual o ticket médio da campanha Arca Parque?"
    provider = DirectorProvider(
        AnalysisDecision(
            goal="Desempenho", analyses=[AnalysisQuestion(title="Vendas", question=question)]
        ),
        [
            FollowUpSuggestion(
                label="Ticket médio",
                question=next_question,
                required_columns=["vl_compra", "cd_compra"],
            )
        ],
    )
    service = _execution_service(provider)
    knowledge = KnowledgeService().get_context()
    first = service.execute_question(
        question="Como foi a campanha?", knowledge_context=knowledge, session_id="one"
    )
    assert first.data[0]["faturamento"] == 2266
    assert first.suggestions[0].label == "Ticket médio"
    provider.decision = AnalysisDecision(
        analyses=[AnalysisQuestion(title="Ticket", question=next_question)]
    )
    second = service.execute_question(
        question="a primeira", knowledge_context=knowledge, session_id="one"
    )
    assert provider.contexts[-2]["question"] == next_question
    assert second.question == "a primeira"
    assert second.data[0]["ticket_medio_por_compra"] == pytest.approx(2266 / 13)
    session = service._conversation_memory.get("one")
    assert len(session.recent_turns) == 2
    assert session.analysis_questions == [next_question]


def test_legacy_multi_query_also_records_one_conversation_turn():
    from test_multi_query_flow import QUESTION

    from app.knowledge.knowledge_service import KnowledgeService

    service = _execution_service()
    result = service.execute_question(
        question=QUESTION, session_id="one", knowledge_context=KnowledgeService().get_context()
    )
    assert result.metadata["successful_plans"] == 2
    assert len(service._conversation_memory.get("one").recent_turns) == 1


def test_director_failure_falls_back_to_existing_engine():
    from app.knowledge.knowledge_service import KnowledgeService

    service = _execution_service(DirectorProvider(None))
    result = service.execute_question(
        question="Qual o faturamento da campanha Arca Parque?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert result.data[0]["faturamento"] == 2266
    assert result.warnings


def test_multi_query_governance_runs_before_narration():
    from test_multi_query_flow import QUESTION

    from app.executor.models import ExecutionResult
    from app.knowledge.knowledge_service import KnowledgeService
    from app.narrator.models import NarratorResponse

    class CapturingNarrator:
        def __init__(self):
            self.rows = []

        def narrate(self, request):
            self.rows.extend(request.execution_result.data)
            return NarratorResponse(answer="Calculado")

    class SensitiveExecutor:
        def execute(self, *, dataframe, plan, knowledge_context):
            return ExecutionResult(
                execution_time=0,
                data=[{"faturamento": 100, "email": "private@example.com", "clientes_unicos": 5}],
                rows_returned=1,
                metadata={"operation_trace": [{"operation": op.type} for op in plan.operations]},
            )

    narrator = CapturingNarrator()
    service = _execution_service(narrator=narrator)
    service._executor = SensitiveExecutor()
    service.execute_question(question=QUESTION, knowledge_context=KnowledgeService().get_context())
    assert narrator.rows
    assert all("email" not in row for row in narrator.rows)


def test_director_deadline_stops_additional_work():
    from app.conversation.director import ConversationDirector
    from app.conversation.models import AnalysisDecision, AnalysisQuestion

    now = [0.0]
    provider = DirectorProvider(
        AnalysisDecision(
            analyses=[
                AnalysisQuestion(title="Um", question="um"),
                AnalysisQuestion(title="Dois", question="dois"),
            ]
        )
    )
    executed = []

    def execute(question):
        executed.append(question)
        now[0] += 61
        return ExecuteResponse(question=question, answer="100", data=[{"total": 100}])

    result = ConversationDirector(provider, clock=lambda: now[0]).run(
        question="Analise",
        session=None,
        schemas={},
        knowledge={},
        execute=execute,
    )
    assert executed == ["um"]
    assert result.metadata["pending_analyses"] == 1
    assert result.suggestions == []


def test_director_history_includes_previous_answer_for_references():
    from app.conversation.director import ConversationDirector

    memory = ConversationMemoryService(InMemorySessionStore())
    _save(memory)
    provider = DirectorProvider(None)
    ConversationDirector(provider).run(
        question="E nessa?",
        session=memory.get("one"),
        schemas={},
        knowledge={},
        execute=lambda _: pytest.fail("No plan"),
    )
    assert (
        provider.contexts[0]["conversation"]["recent_turns"][0]["answer"] == "Resultado calculado."
    )


def test_director_preserves_empty_result_as_business_outcome():
    from app.conversation.director import ConversationDirector
    from app.conversation.models import AnalysisDecision, AnalysisQuestion

    provider = DirectorProvider(
        AnalysisDecision(
            analyses=[
                AnalysisQuestion(title="Campanha", question="Campanha sem compras"),
            ]
        )
    )
    result = ConversationDirector(provider).run(
        question="Vendas?",
        session=None,
        schemas={},
        knowledge={},
        execute=lambda question: ExecuteResponse(
            question=question,
            answer="Não há dados para esse período.",
            data=[],
            metadata={
                "verification": {
                    "passed": False,
                    "checks": {
                        "has_rows": False,
                        "filters_preserved": True,
                    },
                }
            },
        ),
    )
    assert result.answer == "Não há dados para esse período."
    assert result.metadata["successful_analyses"] == 1


def test_unverified_results_do_not_reach_suggestion_provider():
    from app.conversation.director import ConversationDirector
    from app.conversation.models import AnalysisDecision, AnalysisQuestion

    provider = DirectorProvider(
        AnalysisDecision(
            analyses=[
                AnalysisQuestion(title="Campanha", question="Campanha"),
            ]
        )
    )
    result = ConversationDirector(provider).run(
        question="Vendas?",
        session=None,
        schemas={},
        knowledge={},
        execute=lambda question: ExecuteResponse(
            question=question,
            answer="Número incorreto 999",
            data=[{"total": 999}],
            metadata={"verification": {"passed": False}},
        ),
    )
    assert "999" not in result.answer
    assert result.metadata["failed_analyses"] == 1
    assert len(provider.contexts) == 1


def test_suggestions_check_actual_plan_columns_not_only_provider_declaration():
    from app.conversation.models import AnalysisDecision, AnalysisQuestion, FollowUpSuggestion
    from app.knowledge.knowledge_service import KnowledgeService

    provider = DirectorProvider(
        AnalysisDecision(
            analyses=[
                AnalysisQuestion(
                    title="Vendas",
                    question="Qual o faturamento da campanha Arca Parque?",
                )
            ]
        ),
        [
            FollowUpSuggestion(
                label="Bairros",
                question="Qual bairro mais comprou na campanha Arca Parque?",
                required_columns=["vl_compra"],
            )
        ],
    )
    result = _execution_service(provider).execute_question(
        question="Vendas?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert result.suggestions == []


def test_internal_stage_cannot_start_after_turn_budget():
    from app.conversation.budget import analytical_deadline, remaining_timeout

    now = [0.0]
    with analytical_deadline(1.0, lambda: now[0]):
        assert remaining_timeout(15000) == 1000
        now[0] = 2.0
        with pytest.raises(TimeoutError):
            remaining_timeout(15000)
    assert remaining_timeout(15000) == 15000


def test_short_contextual_question_reaches_director_with_previous_analysis():
    from app.conversation.models import AnalysisDecision, AnalysisQuestion
    from app.knowledge.knowledge_service import KnowledgeService

    provider = DirectorProvider(
        AnalysisDecision(
            analyses=[
                AnalysisQuestion(
                    title="Vendas",
                    question="Qual o faturamento da campanha Arca Parque?",
                )
            ]
        )
    )
    service = _execution_service(provider)
    knowledge = KnowledgeService().get_context()
    service.execute_question(
        question="Qual o faturamento da campanha Arca Parque?",
        session_id="one",
        knowledge_context=knowledge,
    )
    response = service.execute_question(
        question="Quanto vendeu?", session_id="one", knowledge_context=knowledge
    )
    assert response.data[0]["faturamento"] == 2266
    assert provider.contexts[-2]["conversation"]["analysis_questions"] == [
        "Qual o faturamento da campanha Arca Parque?",
    ]


def test_age_suggestion_requires_birth_date_even_if_provider_omits_it():
    from app.conversation.models import AnalysisDecision, AnalysisQuestion, FollowUpSuggestion
    from app.knowledge.knowledge_service import KnowledgeService

    provider = DirectorProvider(
        AnalysisDecision(
            analyses=[
                AnalysisQuestion(
                    title="Vendas",
                    question="Qual o faturamento da campanha Arca Parque?",
                )
            ]
        ),
        [
            FollowUpSuggestion(
                label="Perfil etário",
                question="Qual o perfil etário dos clientes da campanha Arca Parque?",
                required_columns=["sk_cliente"],
            )
        ],
    )
    response = _execution_service(provider).execute_question(
        question="Como foi a campanha?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.suggestions == []

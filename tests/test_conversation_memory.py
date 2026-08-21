from app.memory.conversation import ConversationMemoryService
from app.memory.in_memory import InMemorySessionStore
from app.memory.models import ContextualQuestion
from app.planner.models import ExecutionPlan, PlanEntity, PlanMetric


def _memory() -> ConversationMemoryService:
    return ConversationMemoryService(InMemorySessionStore(), recent_limit=2)


def _record(
    memory: ConversationMemoryService,
    *,
    session_id: str,
    question: str,
    answer: str,
    data: dict,
    entity: str,
    metric: str = "faturamento",
) -> None:
    context = ContextualQuestion(
        original_question=question,
        rewritten_question=question,
        summary="",
        state=memory.get(session_id).state,
    )
    memory.record(
        session_id=session_id,
        context=context,
        answer=answer,
        plan=ExecutionPlan(
            intent="ranking",
            entities=[PlanEntity(name=entity)],
            metrics=[PlanMetric(name=metric)],
        ),
        data=[data],
    )


def test_campaign_reference_carries_confirmed_campaign_and_shopping() -> None:
    memory = _memory()
    _record(
        memory,
        session_id="one",
        question="Qual campanha mais vendeu?",
        answer="Mães 2026, no Shopping X.",
        entity="campanha",
        data={"nm_promocao": "Mães 2026", "nm_empreendimento": "Shopping X"},
    )

    result = memory.contextualize(
        session_id="one",
        question="Qual loja mais vendeu nessa campanha?",
    )

    assert result.clarification is None
    assert "campanha = Mães 2026" in result.rewritten_question
    assert "shopping = Shopping X" in result.rewritten_question


def test_pronoun_uses_last_confirmed_shopping() -> None:
    memory = _memory()
    _record(
        memory,
        session_id="two",
        question="Qual shopping mais vendeu na campanha Pais 2026?",
        answer="Buriti Shopping.",
        entity="empreendimento",
        data={"nm_promocao": "Pais 2026", "nm_empreendimento": "Buriti Shopping"},
    )

    result = memory.contextualize(session_id="two", question="E qual foi o ticket médio dele?")

    assert "shopping = Buriti Shopping" in result.rewritten_question
    assert "campanha = Pais 2026" in result.rewritten_question


def test_explicit_new_shopping_replaces_previous_and_inherits_analysis() -> None:
    memory = _memory()
    _record(
        memory,
        session_id="three",
        question="Qual foi a loja líder do Buriti?",
        answer="Casas Bahia.",
        entity="loja",
        data={"nm_empreendimento": "Buriti Shopping", "nm_fantasa": "Casas Bahia"},
    )

    result = memory.contextualize(session_id="three", question="E no Guará?")

    assert "shopping = Buriti Shopping" not in result.rewritten_question
    assert "analisar por loja" in result.rewritten_question
    assert "métrica = faturamento" in result.rewritten_question


def test_unknown_reference_requests_clarification_and_sessions_are_isolated() -> None:
    memory = _memory()
    _record(
        memory,
        session_id="known",
        question="Qual campanha mais vendeu?",
        answer="Mães 2026.",
        entity="campanha",
        data={"nm_promocao": "Mães 2026"},
    )

    isolated = memory.contextualize(
        session_id="different",
        question="Qual loja vendeu mais nessa campanha?",
    )

    assert isolated.clarification is not None
    assert "Mães 2026" not in isolated.rewritten_question


def test_old_turns_are_summarized_and_recent_history_is_bounded() -> None:
    memory = _memory()
    for index in range(4):
        _record(
            memory,
            session_id="bounded",
            question=f"Pergunta {index}",
            answer=f"Resposta {index}",
            entity="campanha",
            data={"nm_promocao": f"Campanha {index}"},
        )

    session = memory.get("bounded")
    assert len(session.recent_turns) == 2
    assert "Pergunta 0" in session.summary
    assert "Pergunta 1" in session.summary


def test_context_sent_to_ai_contains_recent_questions_and_answers() -> None:
    memory = _memory()
    _record(
        memory,
        session_id="history",
        question="Qual o top 10 de campanhas em 2026?",
        answer="1. Campanha A\n2. Campanha B",
        entity="campanha",
        data={"nm_promocao": "Campanha A"},
    )

    result = memory.contextualize(
        session_id="history",
        question="E em qual shopping ocorreu a segunda?",
    )

    assert "Usuário: Qual o top 10 de campanhas em 2026?" in result.summary
    assert "Terbie: 1. Campanha A\n2. Campanha B" in result.summary
    assert 'Resultado estruturado: [{"nm_promocao": "Campanha A"}]' in result.summary


def test_correction_asking_only_for_best_reuses_previous_question() -> None:
    memory = _memory()
    _record(
        memory,
        session_id="correction",
        question="Qual a campanha promocional teve melhor resultado em 2026?",
        answer="As 10 campanhas com maior faturamento foram...",
        entity="campanha",
        data={"nm_promocao": "Mães 2026", "nm_empreendimento": "Shopping Sul"},
    )

    result = memory.contextualize(
        session_id="correction",
        question="Quero saber a melhor",
    )

    assert result.rewritten_question == (
        "Qual a campanha promocional teve melhor resultado em 2026?"
    )

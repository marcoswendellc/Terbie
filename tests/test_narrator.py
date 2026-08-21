from fastapi.testclient import TestClient

from app.executor.models import ExecutionResult
from app.main import app
from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.intelligence import (
    BaseNarrativeProvider,
    GeminiNarrativeProvider,
    IntelligentNarrative,
)
from app.narrator.models import NarrativeContext, NarratorRequest
from app.narrator.narrator import TerbieNarrator
from app.planner.models import ExecutionPlan


def _narrator() -> TerbieNarrator:
    return TerbieNarrator(
        context_builder=NarrativeContextBuilder(),
        formatter=NarrativeFormatter(),
    )


def test_gemini_prompt_requests_dynamic_comparison_table_and_variations() -> None:
    provider = GeminiNarrativeProvider(
        api_key="test-key",
        model="gemini-test",
        timeout_ms=10000,
    )
    context = NarrativeContext(
        question="Resuma em uma tabela comparativa as campanhas A e B",
        rows_returned=2,
        data=[
            {"campanha": "A", "faturamento": 100.0},
            {"campanha": "B", "faturamento": 125.0},
        ],
        columns=["campanha", "faturamento"],
        top_row={"campanha": "A", "faturamento": 100.0},
        intent="comparison",
    )

    prompt = provider._prompt(context)

    assert "sem depender de perguntas ou respostas predefinidas" in prompt
    assert "tabela Markdown" in prompt
    assert "variação absoluta e percentual" in prompt
    assert '"faturamento": 125.0' in prompt


def test_gemini_prompt_keeps_single_campaign_winner_and_uses_all_metrics() -> None:
    provider = GeminiNarrativeProvider(
        api_key="test-key",
        model="gemini-test",
        timeout_ms=10000,
    )
    context = NarrativeContext(
        question="Qual foi a melhor campanha em 2026?",
        rows_returned=1,
        data=[
            {
                "nm_promocao": "Mães 2026",
                "nm_empreendimento": "Shopping Sul",
                "faturamento": 1000.0,
                "quantidade_compras": 10,
                "ticket_medio_por_compra": 100.0,
            }
        ],
        columns=[
            "nm_promocao",
            "nm_empreendimento",
            "faturamento",
            "quantidade_compras",
            "ticket_medio_por_compra",
        ],
        top_row={"nm_promocao": "Mães 2026"},
        intent="ranking",
    )

    prompt = provider._prompt(context)

    assert "apenas a vencedora" in prompt
    assert "identifique o shopping" in prompt
    assert '"quantidade_compras": 10' in prompt
    assert '"ticket_medio_por_compra": 100.0' in prompt


class FakeIntelligentProvider(BaseNarrativeProvider):
    def generate(self, context):
        assert context.data == [{"loja": "A", "faturamento": 300.0}]
        return IntelligentNarrative(
            answer="A loja A liderou o resultado calculado, com R$ 300,00.",
            highlights=["Loja A: R$ 300,00"],
        )


def test_intelligent_narrative_is_used_after_execution() -> None:
    narrator = TerbieNarrator(
        context_builder=NarrativeContextBuilder(),
        formatter=NarrativeFormatter(),
        intelligent_provider=FakeIntelligentProvider(),
    )
    execution_result = ExecutionResult(
        data=[{"loja": "A", "faturamento": 300.0}],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=1,
    )

    response = narrator.narrate(
        NarratorRequest(question="O que você percebe?", execution_result=execution_result),
    )

    assert response.answer.startswith("A loja A liderou")
    assert response.metadata["narrative_provider"] == "gemini"


def test_comparison_table_is_guaranteed_even_without_gemini() -> None:
    execution_result = ExecutionResult(
        data=[
            {"nm_promocao": "Arcaparque", "faturamento": 100.0, "quantidade_compras": 4},
            {"nm_promocao": "No Pelo", "faturamento": 125.0, "quantidade_compras": 5},
        ],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=2,
    )

    response = _narrator().narrate(
        NarratorRequest(
            question="Resuma em uma tabela comparativa as campanhas",
            execution_result=execution_result,
            execution_plan=ExecutionPlan(intent="comparison"),
        ),
    )

    assert "| Campanha / comparação | Faturamento | Quantidade de compras |" in response.answer
    assert "| Arcaparque | R$ 100,00 | 4 |" in response.answer
    assert "| No Pelo | R$ 125,00 | 5 |" in response.answer
    assert "| Variação absoluta | R$ 25,00 | 1 |" in response.answer
    assert "| Variação percentual | 25,00% | 25,00% |" in response.answer
    assert "vs." not in response.answer
    assert response.metadata["narrative_provider"] == "deterministic_table"


def test_comparison_table_keeps_missing_side_visible_without_fake_zeroes() -> None:
    execution_result = ExecutionResult(
        data=[
            {
                "campanha_contexto": "Mães 2026 — Buriti Shopping",
                "faturamento": None,
                "quantidade_compras": None,
            },
            {
                "campanha_contexto": "Mães 2026 — Shopping Sul",
                "faturamento": 200.0,
                "quantidade_compras": 2,
            },
        ],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=2,
    )

    response = _narrator().narrate(
        NarratorRequest(
            question="Compare em uma tabela as campanhas",
            execution_result=execution_result,
            execution_plan=ExecutionPlan(intent="comparison"),
        ),
    )

    assert "| Mães 2026 — Buriti Shopping | Sem dados | Sem dados |" in response.answer
    assert "| Mães 2026 — Shopping Sul | R$ 200,00 | 2 |" in response.answer
    assert "Variação" not in response.answer


def test_comparison_without_numeric_results_never_says_only_completed() -> None:
    execution_result = ExecutionResult(
        data=[
            {"campanha_contexto": "No Pelo 360 — Buriti Shopping", "faturamento": None},
            {"campanha_contexto": "Mães 2026 — Buriti Shopping Guará", "faturamento": None},
        ],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=2,
    )

    response = _narrator().narrate(
        NarratorRequest(
            question="Compare as campanhas",
            execution_result=execution_result,
            execution_plan=ExecutionPlan(intent="comparison"),
        ),
    )

    assert response.answer.startswith("Não encontrei dados")
    assert response.answer != "Comparação concluída."


def test_comparative_frame_lists_every_campaign_as_a_table_row() -> None:
    execution_result = ExecutionResult(
        data=[
            {"nm_promocao": "Campanha A", "faturamento": 100.0},
            {"nm_promocao": "Campanha B", "faturamento": 90.0},
            {"nm_promocao": "Campanha C", "faturamento": 80.0},
        ],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=3,
    )

    response = _narrator().narrate(
        NarratorRequest(
            question="Faça um quadro comparativo das campanhas",
            execution_result=execution_result,
            execution_plan=ExecutionPlan(intent="comparison"),
        ),
    )

    assert "| Campanha A | R$ 100,00 |" in response.answer
    assert "| Campanha B | R$ 90,00 |" in response.answer
    assert "| Campanha C | R$ 80,00 |" in response.answer
    assert "Variação absoluta" not in response.answer
    assert response.metadata["narrative_provider"] == "deterministic_table"


def test_ranking_execution_result_highlights_first_row() -> None:
    execution_result = ExecutionResult(
        data=[
            {"nm_fantasa": "Restaurante A", "faturamento": 1234567.89},
            {"nm_fantasa": "Restaurante B", "faturamento": 100.0},
        ],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=2,
    )

    response = _narrator().narrate(
        NarratorRequest(
            question="Quais são os restaurantes com maior faturamento?",
            execution_result=execution_result,
        ),
    )

    assert "Restaurante A" in response.answer
    assert "R$ 1.234.567,89" in response.answer
    assert not response.answer.startswith("Encontrei")
    assert response.highlights == []


def test_empty_execution_result_returns_safe_answer() -> None:
    execution_result = ExecutionResult(
        data=[],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=0,
    )

    response = _narrator().narrate(
        NarratorRequest(question="Pergunta", execution_result=execution_result),
    )

    assert response.answer == "Não há dados suficientes para sustentar uma resposta confiável."
    assert response.highlights == []


def test_formatter_formats_brazilian_currency() -> None:
    assert NarrativeFormatter().currency_brl(1234567.89) == "R$ 1.234.567,89"


def test_narrator_response_contains_required_fields() -> None:
    execution_result = ExecutionResult(
        data=[{"loja": "A", "faturamento": 300.0}],
        metadata={},
        statistics={},
        warnings=["Aviso teste."],
        execution_time=0.01,
        rows_returned=1,
    )

    response = _narrator().narrate(
        NarratorRequest(question="Pergunta", execution_result=execution_result),
    )

    assert response.answer
    assert "Aviso teste." not in response.answer
    assert response.highlights == []
    assert response.warnings == ["Aviso teste."]
    assert response.metadata["technical_warnings"] == ["Aviso teste."]
    assert response.metadata["rows_returned"] == 1


def test_listing_strategy_answers_campaign_question_directly() -> None:
    execution_result = ExecutionResult(
        data=[
            {
                "cd_promocao": "P001",
                "nm_promocao": "Promoção Verão no Arca Parque 2026",
                "sk_dtinicio": 20260114,
                "sk_dtfim": 20260215,
            },
            {
                "cd_promocao": "P002",
                "nm_promocao": "No Pelo 360 com Hugo e Guilherme e Buriti Shopping",
                "sk_dtinicio": 20260319,
                "sk_dtfim": 20260418,
            },
        ],
        metadata={},
        statistics={},
        warnings=["fallback determinístico."],
        execution_time=0.01,
        rows_returned=2,
    )

    response = _narrator().narrate(
        NarratorRequest(
            question="Quais campanhas ocorreram em 2026?",
            execution_result=execution_result,
            execution_plan=ExecutionPlan(intent="list_distinct"),
        ),
    )

    assert response.answer.startswith("Em 2026 ocorreram duas campanhas:")
    assert "Promoção Verão no Arca Parque 2026" in response.answer
    assert "(14/01/2026 a 15/02/2026)" in response.answer
    assert "No Pelo 360 com Hugo e Guilherme e Buriti Shopping" in response.answer
    assert "(19/03/2026 a 18/04/2026)" in response.answer
    assert "Encontrei" not in response.answer
    assert "fallback determinístico" not in response.answer
    assert response.metadata["technical_warnings"] == ["fallback determinístico."]


def test_campaign_listing_requested_as_table_includes_shopping_and_period() -> None:
    execution_result = ExecutionResult(
        data=[
            {
                "nm_promocao": "Promoção Mães 2026",
                "nm_empreendimento": "Shopping Sul",
                "sk_dtinicio": 20260423,
                "sk_dtfim": 20260510,
            },
            {
                "nm_promocao": "Promoção Mães 2026",
                "nm_empreendimento": "Buriti Shopping Guará",
                "sk_dtinicio": 20260424,
                "sk_dtfim": 20260515,
            },
        ],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=2,
    )

    response = _narrator().narrate(
        NarratorRequest(
            question="Mostre em uma tabela quais campanhas ocorreram em 2026?",
            execution_result=execution_result,
            execution_plan=ExecutionPlan(intent="list_distinct"),
        ),
    )

    assert "| Campanha | Shopping | Início | Fim |" in response.answer
    assert "| Promoção Mães 2026 | Shopping Sul | 23/04/2026 | 10/05/2026 |" in response.answer
    assert "| Promoção Mães 2026 | Buriti Shopping Guará | 24/04/2026 | 15/05/2026 |" in response.answer
    assert response.metadata["narrative_provider"] == "deterministic_table"


def test_listing_strategy_uses_friendly_distinct_count() -> None:
    execution_result = ExecutionResult(
        data=[{"categoria": "Alimentacao"}, {"categoria": "Lazer"}],
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=2,
    )

    response = _narrator().narrate(
        NarratorRequest(
            question="Quais categorias existem?",
            execution_result=execution_result,
            execution_plan=ExecutionPlan(intent="list_distinct"),
        ),
    )

    assert response.answer.startswith("Encontrei 2 itens distintos na sua consulta:")


def test_execute_endpoint_returns_200() -> None:
    from app.core.dependencies import provide_execution_service
    from app.narrator.models import ExecuteResponse

    class FakeExecutionService:
        def execute_question(self, *, question: str, knowledge_context):
            _ = question, knowledge_context
            return ExecuteResponse(
                question="Pergunta",
                answer="Resposta determinística.",
                highlights=["Destaque"],
                data=[{"loja": "A"}],
                metadata={},
                warnings=[],
            )

    app.dependency_overrides[provide_execution_service] = lambda: FakeExecutionService()
    try:
        client = TestClient(app)
        response = client.post("/execute", json={"question": "Pergunta"})
    finally:
        app.dependency_overrides.pop(provide_execution_service, None)

    assert response.status_code == 200
    assert response.json()["answer"] == "Resposta determinística."


def test_narrator_draft_endpoint_returns_200() -> None:
    client = TestClient(app)

    response = client.post(
        "/narrator/draft",
        json={
            "question": "Pergunta",
            "execution_result": {
                "data": [{"loja": "A", "faturamento": 300.0}],
                "metadata": {},
                "statistics": {},
                "warnings": [],
                "execution_time": 0.01,
                "rows_returned": 1,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"]

from app.executor.models import ExecutionResult
from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.models import NarratorRequest
from app.narrator.narrator import TerbieNarrator
from app.planner.models import ExecutionPlan


def _narrate(
    *,
    question: str,
    data: list[dict[str, object]],
    requested_limit: int | None,
    intent: str = "ranking",
):
    ranking_metadata = (
        {
            "requested_limit": requested_limit,
            "executed_limit": requested_limit,
        }
        if requested_limit is not None
        else {}
    )
    result = ExecutionResult(
        data=data,
        metadata={"ranking": ranking_metadata},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=len(data),
    )
    narrator = TerbieNarrator(
        context_builder=NarrativeContextBuilder(),
        formatter=NarrativeFormatter(),
    )
    return narrator.narrate(
        NarratorRequest(
            question=question,
            execution_result=result,
            execution_plan=ExecutionPlan(intent=intent),
        ),
    )


def _revenue_rows(count: int) -> list[dict[str, object]]:
    return [
        {"nm_fantasa": f"Loja {index}", "faturamento": float((count - index + 1) * 1000)}
        for index in range(1, count + 1)
    ]


def test_top_one_keeps_single_winner_answer() -> None:
    response = _narrate(
        question="Qual foi a loja que mais vendeu na campanha Arca Parque?",
        data=_revenue_rows(1),
        requested_limit=1,
    )

    assert response.answer == (
        "A loja com maior faturamento na campanha Arca Parque foi Loja 1, "
        "com R$ 1.000,00."
    )
    assert "1. Loja" not in response.answer


def test_top_three_lists_all_three_rows_in_received_order() -> None:
    data = [
        {"nm_fantasa": "Terceira no alfabeto", "faturamento": 3000.0},
        {"nm_fantasa": "Primeira no alfabeto", "faturamento": 2000.0},
        {"nm_fantasa": "Segunda no alfabeto", "faturamento": 1000.0},
    ]
    response = _narrate(
        question="Quais foram as 3 lojas que mais venderam?",
        data=data,
        requested_limit=3,
    )

    assert response.answer.splitlines()[-3:] == [
        "1. Terceira no alfabeto — R$ 3.000,00",
        "2. Primeira no alfabeto — R$ 2.000,00",
        "3. Segunda no alfabeto — R$ 1.000,00",
    ]


def test_top_ten_lists_ten_rows_with_brazilian_currency() -> None:
    response = _narrate(
        question="Quais foram as 10 lojas que mais venderam na campanha Arca Parque?",
        data=_revenue_rows(10),
        requested_limit=10,
    )

    assert response.answer.startswith(
        "As 10 lojas com maior faturamento na campanha Arca Parque foram:",
    )
    assert response.answer.count("\n") == 11
    assert "1. Loja 1 — R$ 10.000,00" in response.answer
    assert "10. Loja 10 — R$ 1.000,00" in response.answer


def test_ranking_with_fewer_rows_reports_available_count_and_lists_all() -> None:
    response = _narrate(
        question="Quais foram as 10 lojas que mais venderam?",
        data=_revenue_rows(3),
        requested_limit=10,
    )

    assert response.answer.startswith(
        "Foram encontradas 3 lojas com maior faturamento, de 10 solicitadas:",
    )
    assert response.answer.splitlines()[-1] == "3. Loja 3 — R$ 1.000,00"


def test_purchase_count_ranking_lists_every_position() -> None:
    response = _narrate(
        question="Top 3 lojas por quantidade de compras",
        data=[
            {"nm_fantasa": "A", "quantidade_compras": 30},
            {"nm_fantasa": "B", "quantidade_compras": 20},
            {"nm_fantasa": "C", "quantidade_compras": 10},
        ],
        requested_limit=3,
    )

    assert response.answer.splitlines()[-3:] == [
        "1. A — 30",
        "2. B — 20",
        "3. C — 10",
    ]


def test_simple_non_ranking_metric_keeps_current_behavior() -> None:
    response = _narrate(
        question="Qual foi o faturamento?",
        data=[{"faturamento": 44190.0}],
        requested_limit=None,
        intent="metric_query",
    )

    assert response.answer == "O faturamento é R$ 44.190,00."

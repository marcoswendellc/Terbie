from app.executor.models import ExecutionResult
from app.insights.generator import InsightGenerator
from app.insights.models import Insight, InsightResult
from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.models import NarratorRequest
from app.narrator.narrator import TerbieNarrator
from app.planner.models import ExecutionPlan


def _execution_result(data: list[dict[str, object]], *, rows: int | None = None) -> ExecutionResult:
    return ExecutionResult(
        data=data,
        metadata={},
        statistics={},
        warnings=[],
        execution_time=0.01,
        rows_returned=rows if rows is not None else len(data),
    )


def test_comparison_insights_identify_winners_and_recommendations() -> None:
    result = InsightGenerator().generate(
        _execution_result(
            [
                {
                    "nm_promocao": "Arca",
                    "faturamento": 100.0,
                    "ticket_medio": 50.0,
                    "quantidade_compras": 2,
                    "clientes_unicos": 2,
                },
                {
                    "nm_promocao": "No Pelo",
                    "faturamento": 200.0,
                    "ticket_medio": 100.0,
                    "quantidade_compras": 3,
                    "clientes_unicos": 3,
                },
            ],
        ),
        analytical_plan=None,
        execution_plan=ExecutionPlan(intent="comparison"),
    )

    assert any(insight.title == "Maior faturamento" for insight in result.insights)
    assert any(insight.type == "dominance" for insight in result.insights)
    assert "No Pelo" in result.summary
    assert "Comparar segmentos participantes" in result.recommendations


def test_ranking_insights_identify_top_bottom_share_and_gap() -> None:
    result = InsightGenerator().generate(
        _execution_result(
            [
                {"loja": "A", "faturamento": 300.0},
                {"loja": "B", "faturamento": 100.0},
            ],
        ),
        analytical_plan=None,
        execution_plan=ExecutionPlan(intent="ranking"),
    )

    assert {insight.type for insight in result.insights} >= {"winner", "minimum", "share", "gap"}
    assert result.recommendations == ["Ver ticket médio", "Ver crescimento", "Ver clientes"]


def test_metric_insights_describe_single_indicator() -> None:
    result = InsightGenerator().generate(
        _execution_result([{"faturamento": 500.0}]),
        analytical_plan=None,
        execution_plan=ExecutionPlan(),
    )

    assert result.insights[0].type == "metric"
    assert result.insights[0].metric == "faturamento"


def test_listing_insights_count_distinct_items_without_repeating_rows() -> None:
    result = InsightGenerator().generate(
        _execution_result(
            [
                {"cd_promocao": "P1", "nm_promocao": "A"},
                {"cd_promocao": "P2", "nm_promocao": "B"},
            ],
        ),
        analytical_plan=None,
        execution_plan=ExecutionPlan(intent="list_distinct"),
    )

    assert result.insights[0].title == "Quantidade encontrada"
    assert result.insights[0].value == 2
    assert result.summary == "Encontrei 2 campanhas: A; B."


def test_narrator_communicates_insight_result_without_calculating() -> None:
    narrator = TerbieNarrator(
        context_builder=NarrativeContextBuilder(),
        formatter=NarrativeFormatter(),
    )
    insight_result = InsightResult(
        insights=[
            Insight(
                id="i1",
                type="winner",
                title="Maior faturamento",
                description="No Pelo liderou em faturamento.",
            ),
        ],
        summary="No Pelo apresentou desempenho superior.",
        recommendations=["Comparar bairros", "Comparar ticket por loja"],
    )

    response = narrator.narrate(
        NarratorRequest(
            question="Compare campanhas",
            execution_result=_execution_result([{"campanha": "No Pelo", "faturamento": 100.0}]),
            execution_plan=ExecutionPlan(intent="comparison"),
            insight_result=insight_result,
        ),
    )

    assert response.answer.startswith("Comparando as campanhas")
    assert "No Pelo apresentou desempenho superior." in response.answer
    assert "No Pelo liderou em faturamento." in response.answer
    assert "Você também pode analisar" in response.answer
    assert response.insights[0]["title"] == "Maior faturamento"
    assert response.recommendations == ["Comparar bairros", "Comparar ticket por loja"]

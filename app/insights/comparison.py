from typing import Any

from app.executor.models import ExecutionResult
from app.insights.models import Insight, InsightResult


class ComparisonInsightAnalyzer:
    _METRICS = {
        "faturamento": "Maior faturamento",
        "ticket_medio": "Maior ticket médio",
        "quantidade_compras": "Maior quantidade de compras",
        "clientes_unicos": "Maior quantidade de clientes",
    }

    def generate(
        self,
        *,
        execution_result: ExecutionResult,
        analytical_plan: object | None,
        execution_plan: object | None,
    ) -> InsightResult:
        _ = analytical_plan, execution_plan
        rows = execution_result.data
        if len(rows) < 2:
            return InsightResult(
                summary="Não há entidades suficientes para comparação.",
                recommendations=[],
            )

        label_column = self._label_column(rows)
        insights = [
            insight
            for metric, title in self._METRICS.items()
            if (insight := self._winner_insight(rows, label_column, metric, title)) is not None
        ]
        insights.extend(self._dominance_insights(insights, rows))

        summary = self._summary(insights)
        return InsightResult(
            insights=insights,
            summary=summary,
            recommendations=[
                "Comparar segmentos participantes",
                "Comparar bairros",
                "Comparar ticket por loja",
                "Comparar clientes únicos",
            ],
        )

    def _winner_insight(
        self,
        rows: list[dict[str, Any]],
        label_column: str,
        metric: str,
        title: str,
    ) -> Insight | None:
        metric_rows = [row for row in rows if isinstance(row.get(metric), int | float)]
        if not metric_rows:
            return None

        ordered_rows = sorted(metric_rows, key=lambda row: float(row[metric]), reverse=True)
        winner = ordered_rows[0]
        runner_up = ordered_rows[1] if len(ordered_rows) > 1 else None
        winner_value = float(winner[metric])
        runner_up_value = float(runner_up[metric]) if runner_up is not None else 0.0
        absolute_difference = winner_value - runner_up_value
        percent_difference = (
            absolute_difference / runner_up_value
            if runner_up_value
            else None
        )
        winner_label = str(winner.get(label_column))

        return Insight(
            id=f"comparison_{metric}_winner",
            type="winner",
            title=title,
            description=self._description(
                entity=winner_label,
                metric=metric,
                absolute_difference=absolute_difference,
                percent_difference=percent_difference,
            ),
            severity="info",
            confidence=0.95,
            metric=metric,
            entity=winner_label,
            value=winner_value,
            metadata={
                "absolute_difference": absolute_difference,
                "percent_difference": percent_difference,
                "runner_up": runner_up.get(label_column) if runner_up is not None else None,
            },
        )

    def _dominance_insights(
        self,
        insights: list[Insight],
        rows: list[dict[str, Any]],
    ) -> list[Insight]:
        _ = rows
        winner_entities = [
            insight.entity
            for insight in insights
            if insight.type == "winner" and insight.entity is not None
        ]
        if len(winner_entities) < len(self._METRICS):
            return []

        if len(set(winner_entities)) != 1:
            return []

        entity = winner_entities[0]
        return [
            Insight(
                id="comparison_all_metrics_winner",
                type="dominance",
                title="Desempenho superior em todos os indicadores",
                description=(
                    f"{entity} apresentou desempenho superior em todos os indicadores "
                    "analisados."
                ),
                severity="high",
                confidence=0.92,
                entity=entity,
                metadata={"metrics": list(self._METRICS)},
            ),
        ]

    def _summary(self, insights: list[Insight]) -> str:
        dominance = next((insight for insight in insights if insight.type == "dominance"), None)
        if dominance is not None:
            return dominance.description

        winner = next((insight for insight in insights if insight.type == "winner"), None)
        return winner.description if winner is not None else "Comparação concluída."

    def _description(
        self,
        *,
        entity: str,
        metric: str,
        absolute_difference: float,
        percent_difference: float | None,
    ) -> str:
        label = metric.replace("_", " ")
        if percent_difference is None:
            return (
                f"{entity} liderou em {label}, "
                f"com diferença absoluta de {absolute_difference:.2f}."
            )

        return (
            f"{entity} liderou em {label}, com diferença de "
            f"{absolute_difference:.2f} ({percent_difference:.1%})."
        )

    def _label_column(self, rows: list[dict[str, Any]]) -> str:
        for column in rows[0]:
            if not isinstance(rows[0].get(column), int | float):
                return column

        return next(iter(rows[0]), "entity")

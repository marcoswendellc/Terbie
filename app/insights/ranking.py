from typing import Any

from app.executor.models import ExecutionResult
from app.insights.models import Insight, InsightResult


class RankingInsightAnalyzer:
    def generate(
        self,
        *,
        execution_result: ExecutionResult,
        analytical_plan: object | None,
        execution_plan: object | None,
    ) -> InsightResult:
        _ = analytical_plan, execution_plan
        rows = execution_result.data
        if not rows:
            return InsightResult(summary="Ranking sem dados para análise.")

        label_column, metric_column = self._columns(rows)
        if label_column is None or metric_column is None:
            return InsightResult(
                summary="Ranking sem colunas suficientes para gerar insights.",
                recommendations=["Revisar o indicador da análise"],
            )

        metric_rows = [row for row in rows if isinstance(row.get(metric_column), int | float)]
        if not metric_rows:
            return InsightResult(summary="Ranking sem indicador numérico para análise.")

        ordered_rows = sorted(metric_rows, key=lambda row: float(row[metric_column]), reverse=True)
        top = ordered_rows[0]
        bottom = ordered_rows[-1]
        second = ordered_rows[1] if len(ordered_rows) > 1 else None
        total = sum(float(row[metric_column]) for row in ordered_rows)
        top_value = float(top[metric_column])
        second_value = float(second[metric_column]) if second is not None else 0.0
        share = top_value / total if total else 0.0
        distance = top_value - second_value

        insights = [
            Insight(
                id="ranking_top_value",
                type="winner",
                title="Maior valor",
                description=f"{top[label_column]} lidera o ranking em {metric_column}.",
                metric=metric_column,
                entity=str(top[label_column]),
                value=top_value,
                metadata={"share": share},
            ),
            Insight(
                id="ranking_bottom_value",
                type="minimum",
                title="Menor valor",
                description=f"{bottom[label_column]} aparece com o menor valor do ranking.",
                metric=metric_column,
                entity=str(bottom[label_column]),
                value=float(bottom[metric_column]),
            ),
            Insight(
                id="ranking_top_share",
                type="share",
                title="Participação do primeiro colocado",
                description=f"O primeiro colocado representa {share:.1%} do total analisado.",
                metric=metric_column,
                entity=str(top[label_column]),
                value=share,
            ),
            Insight(
                id="ranking_distance_to_second",
                type="gap",
                title="Distância para o segundo colocado",
                description=f"A distância para o segundo colocado é de {distance:.2f}.",
                metric=metric_column,
                entity=str(top[label_column]),
                value=distance,
            ),
        ]
        return InsightResult(
            insights=insights,
            summary=insights[0].description,
            recommendations=["Ver ticket médio", "Ver crescimento", "Ver clientes"],
        )

    def _columns(self, rows: list[dict[str, Any]]) -> tuple[str | None, str | None]:
        first_row = rows[0]
        metric_column = next(
            (
                column
                for column, value in first_row.items()
                if isinstance(value, int | float)
            ),
            None,
        )
        if metric_column is None:
            return None, None

        label_column = next(
            (column for column in first_row if column != metric_column),
            None,
        )
        if label_column is None:
            return None, metric_column

        return label_column, metric_column

from app.executor.models import ExecutionResult
from app.insights.models import Insight, InsightResult


class MetricInsightAnalyzer:
    def generate(
        self,
        *,
        execution_result: ExecutionResult,
        analytical_plan: object | None,
        execution_plan: object | None,
    ) -> InsightResult:
        _ = analytical_plan, execution_plan
        if not execution_result.data:
            return InsightResult(summary="Indicador sem dados para análise.")

        row = execution_result.data[0]
        metric_column = next(
            (column for column, value in row.items() if isinstance(value, int | float)),
            None,
        )
        if metric_column is None:
            return InsightResult(summary="Nenhum indicador numérico foi identificado.")

        insight = Insight(
            id=f"metric_{metric_column}_value",
            type="metric",
            title="Valor do indicador",
            description=f"O indicador {metric_column.replace('_', ' ')} foi calculado.",
            metric=metric_column,
            value=row[metric_column],
            metadata={"context": "single_metric"},
        )
        return InsightResult(
            insights=[insight],
            summary=insight.description,
            recommendations=["Comparar por período", "Abrir por loja", "Ver tendência"],
        )

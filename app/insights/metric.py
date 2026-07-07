from app.executor.models import ExecutionResult
from app.insights.models import Insight, InsightResult
from app.narrator.formatter import NarrativeFormatter


class MetricInsightAnalyzer:
    _LABELS = {
        "faturamento": "O faturamento",
        "ticket_medio_por_compra": "o ticket médio por compra",
        "ticket_medio_por_cliente": "o ticket médio por cliente",
        "quantidade_compras": "o volume de notas cadastradas",
        "clientes_unicos": "os clientes únicos",
    }

    def __init__(self, formatter: NarrativeFormatter | None = None) -> None:
        self._formatter = formatter or NarrativeFormatter()

    def generate(
        self,
        *,
        execution_result: ExecutionResult,
        analytical_plan: object | None,
        execution_plan: object | None,
    ) -> InsightResult:
        _ = analytical_plan
        if not execution_result.data:
            return InsightResult(summary="Indicador sem dados para análise.")

        row = execution_result.data[0]
        metric_names = self._metric_names(execution_plan=execution_plan, row=row)
        insights = [
            Insight(
                id=f"metric_{metric_name}_value",
                type="metric",
                title=self._LABELS.get(metric_name, metric_name.replace("_", " ").title()),
                description=self._phrase(metric_name=metric_name, value=row[metric_name]),
                metric=metric_name,
                value=row[metric_name],
                metadata={"context": "metric_query"},
            )
            for metric_name in metric_names
            if metric_name in row
        ]

        if not insights:
            return InsightResult(summary="Nenhum indicador numérico foi identificado.")

        return InsightResult(
            insights=insights,
            summary=self._join([insight.description for insight in insights]),
            recommendations=[],
        )

    def _metric_names(self, *, execution_plan: object | None, row: dict[str, object]) -> list[str]:
        plan_metrics = getattr(execution_plan, "metrics", [])
        names = [
            metric.name
            for metric in plan_metrics
            if getattr(metric, "name", None) in row
        ]
        if names:
            return names

        return [column for column, value in row.items() if isinstance(value, int | float)]

    def _phrase(self, *, metric_name: str, value: object) -> str:
        label = self._LABELS.get(metric_name, f"O indicador {metric_name.replace('_', ' ')}")
        if metric_name in {
            "faturamento",
            "ticket_medio_por_compra",
            "ticket_medio_por_cliente",
        }:
            return f"{label} foi de {self._formatter.currency_brl(float(value or 0))}"

        if metric_name == "quantidade_compras":
            return f"{label} foi de {self._formatter.integer(int(value or 0))} compras"

        if metric_name == "clientes_unicos":
            return f"{label} foram {self._formatter.integer(int(value or 0))}"

        return f"{label} foi {value}"

    def _join(self, phrases: list[str]) -> str:
        if len(phrases) == 1:
            return phrases[0] + "."

        return ", ".join(phrases[:-1]) + " e " + phrases[-1] + "."


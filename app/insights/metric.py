from app.executor.models import ExecutionResult
from app.insights.models import Insight, InsightResult
from app.narrator.formatter import NarrativeFormatter


class MetricInsightAnalyzer:
    _LABELS = {
        "faturamento": "O faturamento",
        "ticket_medio_por_compra": "o ticket m\u00e9dio por compra",
        "ticket_medio_por_cliente": "o ticket m\u00e9dio por cliente",
        "quantidade_compras": "o volume de notas cadastradas",
        "clientes_unicos": "os clientes \u00fanicos",
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
            return InsightResult(summary="Indicador sem dados para an\u00e1lise.")

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
            return InsightResult(summary="Nenhum indicador num\u00e9rico foi identificado.")

        if len(insights) == 1 and getattr(execution_plan, "intent", None) == "metric_query":
            metric_name = metric_names[0]
            return InsightResult(
                insights=[],
                summary=self._single_metric_summary(
                    metric_name=metric_name,
                    value=row[metric_name],
                    execution_plan=execution_plan,
                ),
                recommendations=[],
            )

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

    def _single_metric_summary(
        self,
        *,
        metric_name: str,
        value: object,
        execution_plan: object | None,
    ) -> str:
        context = self._filter_context(execution_plan)
        if metric_name == "quantidade_compras":
            if context:
                return (
                    f"Foram cadastradas {self._formatter.integer(int(value or 0))} "
                    f"notas {context}."
                )

            return f"Foram cadastradas {self._formatter.integer(int(value or 0))} notas."

        if metric_name == "faturamento":
            if context:
                return (
                    f"O faturamento {context} foi de "
                    f"{self._formatter.currency_brl(float(value or 0))}."
                )

            return f"O faturamento foi de {self._formatter.currency_brl(float(value or 0))}."

        if metric_name == "ticket_medio_por_compra":
            return (
                "O ticket m\u00e9dio por compra foi de "
                f"{self._formatter.currency_brl(float(value or 0))}."
            )

        if metric_name == "ticket_medio_por_cliente":
            return (
                "O ticket m\u00e9dio por cliente foi de "
                f"{self._formatter.currency_brl(float(value or 0))}."
            )

        if metric_name == "clientes_unicos":
            return (
                f"Foram identificados {self._formatter.integer(int(value or 0))} "
                "clientes \u00fanicos."
            )

        return self._phrase(metric_name=metric_name, value=value) + "."

    def _filter_context(self, execution_plan: object | None) -> str:
        operations = getattr(execution_plan, "operations", [])
        order = {
            "nm_fantasa": 10,
            "nm_segmento": 20,
            "bairro": 30,
            "cidade": 40,
            "nm_empreendimento": 50,
            "nm_promocao": 60,
        }
        filters = sorted(
            [
                operation
                for operation in operations
                if getattr(operation, "type", None) == "filter"
                and getattr(operation, "field", None) in order
                and operation.parameters.get("operator", "equals") == "equals"
                and operation.parameters.get("value") is not None
            ],
            key=lambda operation: order[str(operation.field)],
        )

        phrases: list[str] = []
        for operation in filters:
            field = str(operation.field)
            value = self._friendly_filter_value(field, str(operation.parameters["value"]))
            if field == "nm_fantasa":
                phrases.append(f"da loja {value}")
            elif field == "nm_segmento":
                phrases.append(f"do segmento {value}")
            elif field == "bairro":
                phrases.append(f"do bairro {value}")
            elif field == "cidade":
                phrases.append(f"da cidade {value}")
            elif field == "nm_empreendimento":
                phrases.append(f"no empreendimento {value}")
            elif field == "nm_promocao":
                phrases.append(f"na campanha {value}")

        return " ".join(phrases)

    def _friendly_filter_value(self, field: str, value: str) -> str:
        if field == "nm_promocao":
            normalized = value.casefold()
            if "no pelo" in normalized:
                return "No Pelo"
            if "arca" in normalized:
                return "Arcaparque"

        return value

    def _join(self, phrases: list[str]) -> str:
        if len(phrases) == 1:
            return phrases[0] + "."

        return ", ".join(phrases[:-1]) + " e " + phrases[-1] + "."

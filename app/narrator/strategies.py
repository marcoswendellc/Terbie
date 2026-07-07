from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.narrator.formatter import NarrativeFormatter
from app.narrator.models import NarrativeContext


class ResponseStrategy(ABC):
    def __init__(self, formatter: NarrativeFormatter) -> None:
        self._formatter = formatter

    @abstractmethod
    def can_handle(self, context: NarrativeContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def answer(self, context: NarrativeContext) -> str:
        raise NotImplementedError

    def highlights(self, context: NarrativeContext) -> list[str]:
        _ = context
        return []


class ListingStrategy(ResponseStrategy):
    def can_handle(self, context: NarrativeContext) -> bool:
        return context.intent == "list_distinct" or (
            context.rows_returned > 0
            and not context.metric_columns
            and bool(context.dimension_columns)
        )

    def answer(self, context: NarrativeContext) -> str:
        if self._is_promotion_listing(context):
            return self._promotion_answer(context)

        intro = self._listing_intro(context)
        items = [
            f"• {self._row_label(row, context.dimension_columns)}"
            for row in context.data
        ]
        return "\n\n".join([intro, *items])

    def highlights(self, context: NarrativeContext) -> list[str]:
        return [
            self._row_label(row, context.dimension_columns)
            for row in context.data[:3]
        ]

    def _is_promotion_listing(self, context: NarrativeContext) -> bool:
        return {"cd_promocao", "nm_promocao"}.issubset(set(context.columns))

    def _promotion_answer(self, context: NarrativeContext) -> str:
        year = self._year_from_question(context.question)
        count_text = self._count_text(
            context.rows_returned,
            singular="uma campanha",
            plural="campanhas",
        )
        if year is None:
            intro = f"No período analisado ocorreram {count_text}:"
        else:
            intro = f"Em {year} ocorreram {count_text}:"

        items = []
        for row in context.data:
            name = row.get("nm_promocao") or row.get("cd_promocao")
            start = self._date(row.get("sk_dtinicio"))
            end = self._date(row.get("sk_dtfim"))
            period = f"\n({start} a {end})" if start and end else ""
            items.append(f"• {name}{period}")

        return "\n\n".join([intro, *items])

    def _listing_intro(self, context: NarrativeContext) -> str:
        count_text = (
            "1 item distinto"
            if context.rows_returned == 1
            else f"{self._formatter.integer(context.rows_returned)} itens distintos"
        )
        return f"Encontrei {count_text} na sua consulta:"

    def _row_label(self, row: dict[str, Any], dimension_columns: list[str]) -> str:
        values = [
            self._formatter.value(column, row[column])
            for column in dimension_columns
            if column in row and row[column] is not None
        ]
        return " - ".join(values) if values else "Item sem descrição"

    def _year_from_question(self, question: str) -> str | None:
        for token in question.split():
            normalized = token.strip(".,;:!?()[]{}")
            if normalized.isdigit() and len(normalized) == 4:
                return normalized

        return None

    def _date(self, value: object) -> str | None:
        if value is None:
            return None

        raw_value = str(value).replace(".0", "").strip()
        try:
            return datetime.strptime(raw_value, "%Y%m%d").strftime("%d/%m/%Y")
        except ValueError:
            return raw_value

    def _count_text(self, count: int, *, singular: str, plural: str) -> str:
        if count == 1:
            return singular

        return f"{self._number_name(count)} {plural}"

    def _number_name(self, count: int) -> str:
        names = {
            2: "duas",
            3: "três",
            4: "quatro",
            5: "cinco",
            6: "seis",
            7: "sete",
            8: "oito",
            9: "nove",
            10: "dez",
        }
        return names.get(count, self._formatter.integer(count))


class RankingStrategy(ResponseStrategy):
    def can_handle(self, context: NarrativeContext) -> bool:
        return bool(context.dimension_columns and context.metric_columns)

    def answer(self, context: NarrativeContext) -> str:
        top_row = context.top_row or {}
        dimension_column = context.dimension_columns[0]
        metric_column = context.metric_columns[0]
        dimension = self._formatter.value(dimension_column, top_row.get(dimension_column))
        metric = self._formatter.value(metric_column, top_row.get(metric_column))

        if context.rows_returned == 1:
            return f"{dimension} lidera a análise, com {metric}."

        return f"{dimension} aparece como principal destaque, com {metric}."

    def highlights(self, context: NarrativeContext) -> list[str]:
        if context.top_row is None or not context.dimension_columns or not context.metric_columns:
            return []

        dimension_column = context.dimension_columns[0]
        metric_column = context.metric_columns[0]
        dimension = self._formatter.value(dimension_column, context.top_row[dimension_column])
        metric = self._formatter.value(metric_column, context.top_row[metric_column])
        return [self._formatter.ranking_text(dimension=dimension, metric=metric)]


class MetricStrategy(ResponseStrategy):
    def can_handle(self, context: NarrativeContext) -> bool:
        return bool(context.metric_columns) and not context.dimension_columns

    def answer(self, context: NarrativeContext) -> str:
        top_row = context.top_row or {}
        metric_column = context.metric_columns[0]
        metric = self._formatter.value(metric_column, top_row.get(metric_column))
        metric_name = metric_column.replace("_", " ")
        return f"O {metric_name} é {metric}."

    def highlights(self, context: NarrativeContext) -> list[str]:
        if context.top_row is None or not context.metric_columns:
            return []

        metric_column = context.metric_columns[0]
        return [self._formatter.value(metric_column, context.top_row[metric_column])]


class ComparisonStrategy(ResponseStrategy):
    def can_handle(self, context: NarrativeContext) -> bool:
        return context.intent in {"comparison", "compare_periods"}

    def answer(self, context: NarrativeContext) -> str:
        if not context.data:
            return "Não há dados suficientes para sustentar uma comparação confiável."

        label_column = (
            context.dimension_columns[0]
            if context.dimension_columns
            else context.columns[0]
        )
        revenue_winner = self._max_row(context.data, "faturamento")
        ticket_winner = self._max_row(context.data, "ticket_medio")
        revenue_label = self._formatter.value(label_column, revenue_winner.get(label_column))
        ticket_label = self._formatter.value(label_column, ticket_winner.get(label_column))
        revenue = self._formatter.value("faturamento", revenue_winner.get("faturamento", 0))
        ticket = self._formatter.value("ticket_medio", ticket_winner.get("ticket_medio", 0))

        return (
            f"Comparando as campanhas, {revenue_label} apresentou o maior faturamento, "
            f"com {revenue}, enquanto {ticket_label} teve o maior ticket médio, de {ticket}.\n\n"
            "Resumo dos indicadores:\n"
            "• Faturamento\n"
            "• Ticket médio\n"
            "• Quantidade de compras\n"
            "• Clientes únicos"
        )

    def highlights(self, context: NarrativeContext) -> list[str]:
        if not context.data:
            return []

        label_column = (
            context.dimension_columns[0]
            if context.dimension_columns
            else context.columns[0]
        )
        revenue_winner = self._max_row(context.data, "faturamento")
        label = self._formatter.value(label_column, revenue_winner.get(label_column))
        revenue = self._formatter.value("faturamento", revenue_winner.get("faturamento", 0))
        return [f"{label}, com {revenue} de faturamento"]

    def _max_row(self, rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
        return max(rows, key=lambda row: float(row.get(metric) or 0))


class TrendStrategy(ResponseStrategy):
    def can_handle(self, context: NarrativeContext) -> bool:
        return context.intent in {"trend", "growth"}

    def answer(self, context: NarrativeContext) -> str:
        return RankingStrategy(self._formatter).answer(context)

    def highlights(self, context: NarrativeContext) -> list[str]:
        return RankingStrategy(self._formatter).highlights(context)


class GenericStrategy(ResponseStrategy):
    def can_handle(self, context: NarrativeContext) -> bool:
        _ = context
        return True

    def answer(self, context: NarrativeContext) -> str:
        if context.top_row is None:
            return "Não há dados suficientes para sustentar uma resposta confiável."

        readable_values = []
        for column, value in context.top_row.items():
            if isinstance(value, int | float | Decimal):
                value_text = self._formatter.value(column, value)
            else:
                value_text = str(value)
            readable_values.append(f"{column.replace('_', ' ')}: {value_text}")

        return "O principal recorte da análise é " + "; ".join(readable_values) + "."

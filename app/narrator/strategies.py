import re
import unicodedata
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


class SalesDateRangeStrategy(ResponseStrategy):
    def can_handle(self, context: NarrativeContext) -> bool:
        return context.intent == "sales_date_range"

    def answer(self, context: NarrativeContext) -> str:
        row = context.top_row or {}
        start = self._date(row.get("primeira_venda"))
        end = self._date(row.get("ultima_venda"))
        if start is None:
            return "Não encontrei uma data de venda válida nos dados disponíveis."
        if end is None or end == start:
            return f"Há vendas disponíveis a partir de {start}."
        return f"Há vendas disponíveis de {start} até {end}."

    def _date(self, value: object) -> str | None:
        if value is None:
            return None
        try:
            return datetime.fromisoformat(str(value)).strftime("%d/%m/%Y")
        except ValueError:
            return str(value)


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
        _ = context
        return []

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
    _ANALYSIS_TERMS = (
        "analise",
        "analisa",
        "analisar",
        "desempenho",
        "resumo executivo",
        "principais insights",
        "insights",
        "o que voce percebe",
        "o que percebe",
    )
    _DIMENSION_LABELS = {
        "bairro": ("O", "bairro"),
        "cidade": ("A", "cidade"),
        "genero": ("O", "gênero"),
        "faixa_etaria": ("A", "faixa etária"),
        "idade": ("A", "idade"),
        "nm_segmento": ("O", "segmento"),
        "nm_fantasa": ("A", "loja"),
        "loja": ("A", "loja"),
        "sk_cliente": ("O", "cliente"),
        "nm_promocao": ("A", "campanha"),
    }

    def can_handle(self, context: NarrativeContext) -> bool:
        return bool(context.dimension_columns and context.metric_columns)

    def answer(self, context: NarrativeContext) -> str:
        top_row = context.top_row or {}
        dimension_column = context.dimension_columns[0]
        metric_column = context.metric_columns[0]
        dimension = self._formatter.value(dimension_column, top_row.get(dimension_column))
        metric = self._formatter.value(metric_column, top_row.get(metric_column))

        if self._is_multi_record_ranking(context):
            return self._ranked_list(
                context=context,
                dimension_column=dimension_column,
                metric_column=metric_column,
            )

        if not self._asks_for_analysis(context.question):
            return self._objective_answer(
                context=context,
                dimension_column=dimension_column,
                metric_column=metric_column,
                dimension=dimension,
                metric=metric,
            )

        if context.rows_returned == 1:
            return f"{dimension} lidera a análise, com {metric}."

        return f"{dimension} aparece como principal destaque, com {metric}."

    def highlights(self, context: NarrativeContext) -> list[str]:
        if not self._asks_for_analysis(context.question):
            return []

        if context.top_row is None or not context.dimension_columns or not context.metric_columns:
            return []

        dimension_column = context.dimension_columns[0]
        metric_column = context.metric_columns[0]
        dimension = self._formatter.value(dimension_column, context.top_row[dimension_column])
        metric = self._formatter.value(metric_column, context.top_row[metric_column])
        return [self._formatter.ranking_text(dimension=dimension, metric=metric)]

    def _objective_answer(
        self,
        *,
        context: NarrativeContext,
        dimension_column: str,
        metric_column: str,
        dimension: str,
        metric: str,
    ) -> str:
        article, label = self._DIMENSION_LABELS.get(
            dimension_column,
            ("O", dimension_column.replace("_", " ")),
        )
        context_text = self._campaign_context(context.question)
        objective = self._objective_phrase(metric_column)
        metric_phrase = self._metric_phrase(metric_column=metric_column, metric=metric)
        if self._is_best_campaign_question(context.question, dimension_column, metric_column):
            period = self._year_from_question(context.question)
            if period is not None:
                return f"A melhor campanha em {period}, considerando faturamento, foi {dimension}."

            return f"A melhor campanha, considerando faturamento, foi {dimension}."

        return (
            f"{article} {label} com {objective}{context_text} "
            f"foi {dimension}, com {metric_phrase}."
        )

    def _asks_for_ranked_list(self, question: str) -> bool:
        normalized = self._normalize_text(question)
        return bool(
            re.search(r"\btop\s+\d+\b", normalized)
            or re.search(r"\branking\s+\d+\b", normalized)
            or re.search(r"\branking\s+d(?:a|e|o|os|as)\s+\d+\b", normalized)
            or re.search(r"\b(me\s+)?liste\b", normalized)
            or re.search(
                r"\b(?:quais|liste|mostrar|mostre)\b.*\b\d+\b.*"
                r"\b(?:lojas?|lojistas?|segmentos?|bairros?|cidades?|clientes?)\b",
                normalized,
            )
        )

    def _is_multi_record_ranking(self, context: NarrativeContext) -> bool:
        metadata_rows = context.execution_metadata.get("rows_returned")
        reported_rows = metadata_rows if isinstance(metadata_rows, int) else context.rows_returned
        available_count = min(reported_rows, len(context.data))
        if available_count <= 1:
            return False

        requested_limit = self._requested_limit(context)
        ranking_metadata = context.execution_metadata.get("ranking", {})
        metadata_marks_ranking = isinstance(ranking_metadata, dict) and any(
            isinstance(ranking_metadata.get(field), int)
            for field in ("requested_limit", "executed_limit")
        )
        return bool(
            context.intent == "ranking"
            or requested_limit is not None
            or metadata_marks_ranking
            or self._asks_for_ranked_list(context.question)
        )

    def _requested_limit(self, context: NarrativeContext) -> int | None:
        ranking_metadata = context.execution_metadata.get("ranking", {})
        if isinstance(ranking_metadata, dict):
            for field in ("requested_limit", "executed_limit"):
                value = ranking_metadata.get(field)
                if isinstance(value, int) and value > 0:
                    return value

        normalized = self._normalize_text(context.question)
        patterns = (
            r"\btop\s+(\d+)\b",
            r"\branking(?:\s+d(?:a|e|o|os|as))?\s+(\d+)\b",
            r"\b(?:quais|liste|mostrar|mostre)?\b.*?\b(\d+)\s+"
            r"(?:lojas?|lojistas?|segmentos?|bairros?|cidades?|clientes?)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match is not None:
                return int(match.group(1))
        return None

    def _ranked_list(
        self,
        *,
        context: NarrativeContext,
        dimension_column: str,
        metric_column: str,
    ) -> str:
        _, singular_label = self._DIMENSION_LABELS.get(
            dimension_column,
            ("O", dimension_column.replace("_", " ")),
        )
        plural_label = {
            "loja": "lojas",
            "campanha": "campanhas",
            "segmento": "segmentos",
            "bairro": "bairros",
            "cidade": "cidades",
            "cliente": "clientes",
        }.get(singular_label, f"{singular_label}s")
        campaign_context = self._campaign_context(context.question)
        actual_count = min(context.rows_returned, len(context.data))
        requested_limit = self._requested_limit(context)
        objective = self._objective_phrase(metric_column)
        if requested_limit is not None and actual_count < requested_limit:
            heading = (
                f"Foram encontradas {actual_count} {plural_label} com {objective}"
                f"{campaign_context}, de {requested_limit} solicitadas:"
            )
        else:
            heading = (
                f"As {actual_count} {plural_label} com {objective}"
                f"{campaign_context} foram:"
            )

        lines = []
        for index, row in enumerate(context.data, start=1):
            dimension_value = self._formatter.value(
                dimension_column,
                row.get(dimension_column),
            )
            if len(context.metric_columns) > 1:
                metric_values = "; ".join(
                    f"{self._metric_label(column)}: "
                    f"{self._formatter.value(column, row.get(column))}"
                    for column in context.metric_columns
                )
            else:
                metric_values = self._formatter.value(
                    metric_column,
                    row.get(metric_column),
                )
            lines.append(f"{index}. {dimension_value} — {metric_values}")
        calculation_note = (
            "\n\nContagem: notas únicas cadastradas (cd_compra distinto)."
            if metric_column == "quantidade_compras"
            else ""
        )
        return f"{heading}{calculation_note}\n\n" + "\n".join(lines)

    def _metric_label(self, metric_column: str) -> str:
        return {
            "quantidade_compras": "Quantidade de compras",
            "faturamento": "Valor das compras",
            "clientes_unicos": "Clientes únicos",
            "ticket_medio": "Ticket médio",
            "ticket_medio_por_compra": "Ticket médio por compra",
            "ticket_medio_por_cliente": "Ticket médio por cliente",
        }.get(metric_column, metric_column.replace("_", " ").capitalize())

    def _objective_phrase(self, metric_column: str) -> str:
        if metric_column == "quantidade_compras":
            return "maior participação em volume de notas"
        if metric_column == "faturamento":
            return "maior faturamento"
        if metric_column in {"ticket_medio", "ticket_medio_por_compra"}:
            return "maior ticket médio por compra"
        if metric_column == "ticket_medio_por_cliente":
            return "maior ticket médio por cliente"
        return f"maior {metric_column.replace('_', ' ')}"

    def _metric_phrase(self, *, metric_column: str, metric: str) -> str:
        if metric_column == "quantidade_compras":
            return f"{metric} notas cadastradas"
        return metric

    def _campaign_context(self, question: str) -> str:
        match = re.search(
            r"\b(?:na|no|da|do)\s+campanha\s+(.+?)(?:,|\s+qual\b|\s+exceto\b|$)",
            question,
            flags=re.IGNORECASE,
        )
        if match is None:
            return ""

        campaign = match.group(1).strip(" .?!")
        if not campaign:
            return ""

        return f" na campanha {campaign}"

    def _asks_for_analysis(self, question: str) -> bool:
        normalized = self._normalize_text(question)
        return any(term in normalized for term in self._ANALYSIS_TERMS)

    def _normalize_text(self, text: str) -> str:
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFKD", text.lower())
            if not unicodedata.combining(char)
        )
        return re.sub(r"\s+", " ", without_accents).strip()

    def _is_best_campaign_question(
        self,
        question: str,
        dimension_column: str,
        metric_column: str,
    ) -> bool:
        normalized = self._normalize_text(question)
        return (
            dimension_column == "nm_promocao"
            and metric_column == "faturamento"
            and "melhor campanha" in normalized
        )

    def _year_from_question(self, question: str) -> str | None:
        match = re.search(r"\b(20\d{2}|19\d{2})\b", question)
        return match.group(1) if match is not None else None


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
    _METRIC_LABELS = {
        "faturamento": "Faturamento",
        "quantidade_compras": "Quantidade de compras",
        "clientes_unicos": "Clientes únicos",
        "ticket_medio": "Ticket médio",
        "ticket_medio_por_compra": "Ticket médio por compra",
        "ticket_medio_por_cliente": "Ticket médio por cliente",
    }

    def can_handle(self, context: NarrativeContext) -> bool:
        return context.intent in {"comparison", "compare_periods"}

    def answer(self, context: NarrativeContext) -> str:
        if not context.data:
            return "Não há dados suficientes para sustentar uma comparação confiável."

        if "tabela" in self._normalize(context.question) and len(context.data) >= 2:
            return self._comparison_table(context)

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

    def _comparison_table(self, context: NarrativeContext) -> str:
        label_column = (
            context.dimension_columns[0]
            if context.dimension_columns
            else context.columns[0]
        )
        base_row, compared_row = context.data[:2]
        base_label = self._cell(base_row.get(label_column))
        compared_label = self._cell(compared_row.get(label_column))
        metrics = [
            metric
            for metric in context.metric_columns
            if isinstance(base_row.get(metric), int | float)
            and isinstance(compared_row.get(metric), int | float)
        ]
        lines = [
            "| Campanha / comparação | "
            + " | ".join(
                self._METRIC_LABELS.get(metric, metric.replace("_", " ").title())
                for metric in metrics
            )
            + " |",
            "|---|" + "---:|" * len(metrics),
        ]

        lines.append(self._metric_row(base_label, base_row, metrics))
        lines.append(self._metric_row(compared_label, compared_row, metrics))
        lines.append(
            self._variation_row(
                "Variação absoluta",
                base_row,
                compared_row,
                metrics,
                percentage=False,
            ),
        )
        lines.append(
            self._variation_row(
                "Variação percentual",
                base_row,
                compared_row,
                metrics,
                percentage=True,
            ),
        )

        return "\n".join(lines)

    def _metric_row(
        self,
        label: str,
        row: dict[str, Any],
        metrics: list[str],
    ) -> str:
        values = [self._formatter.value(metric, row[metric]) for metric in metrics]
        return "| " + " | ".join([label, *values]) + " |"

    def _variation_row(
        self,
        label: str,
        base_row: dict[str, Any],
        compared_row: dict[str, Any],
        metrics: list[str],
        *,
        percentage: bool,
    ) -> str:
        values: list[str] = []
        for metric in metrics:
            base_value = float(base_row[metric])
            difference = float(compared_row[metric]) - base_value
            if percentage:
                values.append(
                    self._formatter.percent(difference / base_value)
                    if base_value != 0
                    else "Não aplicável",
                )
            else:
                values.append(self._formatter.value(metric, difference))
        return "| " + " | ".join([label, *values]) + " |"

    def _cell(self, value: object) -> str:
        return str(value).replace("|", "\\|")

    def _normalize(self, text: str) -> str:
        replacements = str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc")
        return text.lower().translate(replacements)


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

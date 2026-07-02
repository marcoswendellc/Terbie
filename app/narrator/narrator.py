from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.models import NarratorRequest, NarratorResponse
from app.narrator.templates import (
    EMPTY_RESULT_TEMPLATE,
    GENERIC_RESULT_TEMPLATE,
    RANKING_TEMPLATE,
    WARNING_TEMPLATE,
)


class TerbieNarrator:
    """Creates deterministic Portuguese narratives from ExecutionResult."""

    def __init__(
        self,
        context_builder: NarrativeContextBuilder,
        formatter: NarrativeFormatter,
    ) -> None:
        self._context_builder = context_builder
        self._formatter = formatter

    def narrate(self, request: NarratorRequest) -> NarratorResponse:
        context = self._context_builder.build(request)
        if context.rows_returned == 0 or context.top_row is None:
            return NarratorResponse(
                answer=EMPTY_RESULT_TEMPLATE,
                summary=None,
                highlights=[],
                warnings=context.warnings,
                metadata={"rows_returned": context.rows_returned, "columns": context.columns},
            )

        highlights = self._highlights(
            context.top_row,
            context.dimension_columns,
            context.metric_columns,
        )
        answer = self._answer(
            rows=context.rows_returned,
            highlights=highlights,
            warnings=context.warnings,
        )

        return NarratorResponse(
            answer=answer,
            summary=GENERIC_RESULT_TEMPLATE.format(rows=context.rows_returned),
            highlights=highlights,
            warnings=context.warnings,
            metadata={"rows_returned": context.rows_returned, "columns": context.columns},
        )

    def _highlights(
        self,
        top_row: dict[str, object],
        dimension_columns: list[str],
        metric_columns: list[str],
    ) -> list[str]:
        if not dimension_columns or not metric_columns:
            return []

        dimension_column = dimension_columns[0]
        metric_column = metric_columns[0]
        dimension_value = self._formatter.value(dimension_column, top_row[dimension_column])
        metric_value = self._formatter.value(metric_column, top_row[metric_column])
        return [
            self._formatter.ranking_text(
                dimension=dimension_value,
                metric=metric_value,
            ),
        ]

    def _answer(self, *, rows: int, highlights: list[str], warnings: list[str]) -> str:
        base_answer = (
            RANKING_TEMPLATE.format(rows=rows, highlight=highlights[0])
            if highlights
            else GENERIC_RESULT_TEMPLATE.format(rows=rows)
        )
        if not warnings:
            return base_answer

        return f"{base_answer} {WARNING_TEMPLATE.format(warnings='; '.join(warnings))}."

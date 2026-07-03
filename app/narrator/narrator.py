from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.models import NarratorRequest, NarratorResponse
from app.narrator.strategies import (
    ComparisonStrategy,
    GenericStrategy,
    ListingStrategy,
    MetricStrategy,
    RankingStrategy,
    ResponseStrategy,
    TrendStrategy,
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
        self._strategies: list[ResponseStrategy] = [
            ListingStrategy(formatter),
            ComparisonStrategy(formatter),
            TrendStrategy(formatter),
            MetricStrategy(formatter),
            RankingStrategy(formatter),
            GenericStrategy(formatter),
        ]

    def narrate(self, request: NarratorRequest) -> NarratorResponse:
        context = self._context_builder.build(request)
        if context.rows_returned == 0 or context.top_row is None:
            return NarratorResponse(
                answer="Não há dados suficientes para sustentar uma resposta confiável.",
                summary=None,
                highlights=[],
                warnings=context.warnings,
                metadata=self._metadata(context),
            )

        strategy = self._strategy_for(context)
        highlights = strategy.highlights(context)

        return NarratorResponse(
            answer=strategy.answer(context),
            summary=None,
            highlights=highlights,
            warnings=context.warnings,
            metadata=self._metadata(context),
        )

    def _strategy_for(self, context) -> ResponseStrategy:
        for strategy in self._strategies:
            if strategy.can_handle(context):
                return strategy

        return self._strategies[-1]

    def _metadata(self, context) -> dict[str, object]:
        metadata: dict[str, object] = {
            "rows_returned": context.rows_returned,
            "columns": context.columns,
        }
        if context.warnings:
            metadata["technical_warnings"] = context.warnings

        return metadata

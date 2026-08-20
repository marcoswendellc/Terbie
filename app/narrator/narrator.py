from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.intelligence import BaseNarrativeProvider
from app.narrator.models import NarratorRequest, NarratorResponse
from app.narrator.strategies import (
    ComparisonStrategy,
    GenericStrategy,
    ListingStrategy,
    MetricStrategy,
    PersonaStrategy,
    RankingStrategy,
    ResponseStrategy,
    SalesDateRangeStrategy,
    TrendStrategy,
)


class TerbieNarrator:
    """Creates deterministic Portuguese narratives from ExecutionResult."""

    def __init__(
        self,
        context_builder: NarrativeContextBuilder,
        formatter: NarrativeFormatter,
        intelligent_provider: BaseNarrativeProvider | None = None,
    ) -> None:
        self._context_builder = context_builder
        self._formatter = formatter
        self._intelligent_provider = intelligent_provider
        self._strategies: list[ResponseStrategy] = [
            SalesDateRangeStrategy(formatter),
            PersonaStrategy(formatter),
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

        if context.intent in {"sales_date_range", "persona", "persona_comparison"}:
            strategy = self._strategy_for(context)
            return NarratorResponse(
                answer=strategy.answer(context),
                summary=None,
                highlights=[],
                warnings=context.warnings,
                metadata=self._metadata(context),
            )

        if (
            context.intent == "list_distinct"
            and "nm_promocao" in context.columns
            and any(term in self._normalize(context.question) for term in ("tabela", "quadro"))
        ):
            strategy = ListingStrategy(self._formatter)
            return NarratorResponse(
                answer=strategy.answer(context),
                summary=None,
                highlights=[],
                warnings=context.warnings,
                metadata={**self._metadata(context), "narrative_provider": "deterministic_table"},
            )

        if self._requires_comparison_table(context):
            strategy = self._strategy_for(context)
            return NarratorResponse(
                answer=strategy.answer(context),
                summary=None,
                highlights=[],
                warnings=context.warnings,
                metadata={**self._metadata(context), "narrative_provider": "deterministic_table"},
            )

        if self._requires_exact_ranking(context):
            strategy = self._strategy_for(context)
            return NarratorResponse(
                answer=strategy.answer(context),
                summary=None,
                highlights=[],
                warnings=context.warnings,
                metadata={
                    **self._metadata(context),
                    "narrative_provider": "deterministic_ranking",
                },
            )

        if context.intent in {"comparison", "compare_periods"} and (
            context.insight_result is None
            or not getattr(context.insight_result, "insights", [])
        ):
            strategy = ComparisonStrategy(self._formatter)
            answer = strategy.answer(context)
            return NarratorResponse(
                answer=answer,
                summary=None,
                highlights=self._deduplicate_highlights(
                    answer=answer,
                    highlights=strategy.highlights(context),
                ),
                warnings=context.warnings,
                metadata={**self._metadata(context), "narrative_provider": "deterministic_comparison"},
            )

        if self._intelligent_provider is not None:
            intelligent = self._intelligent_provider.generate(context)
            if intelligent is not None:
                return NarratorResponse(
                    answer=intelligent.answer,
                    summary=intelligent.summary,
                    highlights=self._deduplicate_highlights(
                        answer=intelligent.answer,
                        highlights=intelligent.highlights,
                    ),
                    warnings=context.warnings,
                    metadata={**self._metadata(context), "narrative_provider": "gemini"},
                )

        if context.insight_result is not None:
            return self._narrate_insights(context)

        strategy = self._strategy_for(context)
        answer = strategy.answer(context)
        highlights = self._deduplicate_highlights(
            answer=answer,
            highlights=strategy.highlights(context),
        )

        return NarratorResponse(
            answer=answer,
            summary=None,
            highlights=highlights,
            warnings=context.warnings,
            metadata=self._metadata(context),
        )

    def _narrate_insights(self, context) -> NarratorResponse:
        insight_result = context.insight_result
        insights = [
            insight.model_dump()
            for insight in getattr(insight_result, "insights", [])
        ]
        recommendations = list(getattr(insight_result, "recommendations", []))
        answer = self._insight_answer(
            context=context,
            summary=str(getattr(insight_result, "summary", "") or ""),
            insights=insights,
            recommendations=recommendations,
        )
        return NarratorResponse(
            answer=answer,
            summary=getattr(insight_result, "summary", None),
            highlights=self._deduplicate_highlights(
                answer=answer,
                highlights=[str(insight["description"]) for insight in insights[:3]],
            ),
            insights=insights,
            recommendations=recommendations,
            warnings=context.warnings,
            metadata=self._metadata(context),
        )

    def _insight_answer(
        self,
        *,
        context,
        summary: str,
        insights: list[dict[str, object]],
        recommendations: list[str],
    ) -> str:
        if context.rows_returned == 0 and not insights:
            return "Não há dados suficientes para sustentar uma resposta confiável."

        parts: list[str] = []
        if summary:
            parts.append(summary)

        winner_insights = [
            insight
            for insight in insights
            if insight.get("type") == "winner"
        ]
        if winner_insights:
            ranking_campaign_answer = self._campaign_ranking_answer(
                context=context,
                winner_insights=winner_insights,
            )
            if ranking_campaign_answer is not None:
                if parts:
                    parts[0] = ranking_campaign_answer
                else:
                    parts.append(ranking_campaign_answer)
                winner_insights = []

        if winner_insights:
            if not parts:
                parts.append("Comparando as campanhas, os principais destaques foram:")
            elif "Comparando" not in parts[0]:
                parts[0] = f"Comparando as campanhas, {parts[0]}"

            descriptions = [
                str(insight["description"])
                for insight in winner_insights[:4]
                if str(insight["description"]) != summary
            ]
            if descriptions:
                parts.append(" ".join(descriptions))
            metric_titles = "\n".join(
                f"• {insight['title']}"
                for insight in winner_insights[:4]
            )
            parts.append(f"Resumo dos indicadores:\n{metric_titles}")

        if recommendations:
            recommendation_lines = "\n".join(
                f"• {recommendation}"
                for recommendation in recommendations[:3]
            )
            parts.append(f"Você também pode analisar:\n\n{recommendation_lines}")

        return "\n\n".join(parts) if parts else "A análise foi concluída."

    def _campaign_ranking_answer(
        self,
        *,
        context,
        winner_insights: list[dict[str, object]],
    ) -> str | None:
        if context.intent != "ranking" or "campanha" not in context.question.lower():
            return None

        first_insight = winner_insights[0]
        entity = first_insight.get("entity")
        if not isinstance(entity, str) or not entity:
            return None

        period = self._year_from_question(context.question) or "período analisado"
        return f"A melhor campanha em {period}, considerando faturamento, foi {entity}."

    def _year_from_question(self, question: str) -> str | None:
        for token in question.split():
            normalized = token.strip(".,;:!?()[]{}")
            if normalized.isdigit() and len(normalized) == 4:
                return normalized

        return None

    def _strategy_for(self, context) -> ResponseStrategy:
        for strategy in self._strategies:
            if strategy.can_handle(context):
                return strategy

        return self._strategies[-1]

    def _requires_comparison_table(self, context) -> bool:
        return context.intent in {"comparison", "compare_periods"} and (
            any(
                term in self._normalize(context.question)
                for term in ("tabela", "quadro", "comparativo")
            )
        )

    def _requires_exact_ranking(self, context) -> bool:
        """Prevent a generative narrator from changing calculated rankings."""
        return context.intent == "ranking" and context.rows_returned > 1

    def _metadata(self, context) -> dict[str, object]:
        metadata: dict[str, object] = {
            "rows_returned": context.rows_returned,
            "columns": context.columns,
        }
        if context.warnings:
            metadata["technical_warnings"] = context.warnings

        return metadata

    def _deduplicate_highlights(self, *, answer: str, highlights: list[str]) -> list[str]:
        normalized_answer = self._normalize(answer)
        deduplicated: list[str] = []
        seen: set[str] = set()
        for highlight in highlights:
            normalized_highlight = self._normalize(highlight)
            if not normalized_highlight or normalized_highlight in seen:
                continue
            if normalized_highlight == normalized_answer:
                continue

            deduplicated.append(highlight)
            seen.add(normalized_highlight)

        return deduplicated

    def _normalize(self, text: str) -> str:
        return " ".join(text.casefold().split())

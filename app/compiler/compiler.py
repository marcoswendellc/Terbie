import logging
import re

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import AnalyticalHypothesis, CompilerRequest, CompilerResponse
from app.context_resolution.context_resolver import ContextResolver
from app.context_resolution.models import ResolvedContext
from app.entity_resolution.entity_resolver import EntityResolver
from app.entity_resolution.models import EntityMatch
from app.knowledge.models import KnowledgeContext
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.reasoning.base import BaseReasoningProvider
from app.reasoning.models import ReasoningContext
from app.semantic.models import SemanticResolution

logger = logging.getLogger(__name__)


class TerbieCompiler:
    """Coordinates natural-language analysis into Terbie analytical IR and draft DSL."""

    def __init__(
        self,
        hypothesis_builder: HypothesisBuilder,
        analytical_planner: AnalyticalPlanner,
        execution_plan_builder: ExecutionPlanBuilder,
        validator: PlanValidator,
        optimizer: PlanOptimizer,
        reasoning_provider: BaseReasoningProvider | None = None,
        entity_resolver: EntityResolver | None = None,
        context_resolver: ContextResolver | None = None,
    ) -> None:
        self._hypothesis_builder = hypothesis_builder
        self._analytical_planner = analytical_planner
        self._execution_plan_builder = execution_plan_builder
        self._validator = validator
        self._optimizer = optimizer
        self._reasoning_provider = reasoning_provider
        self._entity_resolver = entity_resolver or EntityResolver()
        self._context_resolver = context_resolver or ContextResolver(
            entity_resolver=self._entity_resolver,
        )

    def compile(self, request: CompilerRequest) -> CompilerResponse:
        semantic_resolution = (
            request.semantic_resolution
            if isinstance(request.semantic_resolution, SemanticResolution)
            else None
        )
        knowledge_context = (
            request.knowledge_context
            if isinstance(request.knowledge_context, KnowledgeContext)
            else None
        )

        hypothesis = self._build_hypothesis(
            question=request.question,
            semantic_resolution=semantic_resolution,
            knowledge_context=knowledge_context,
            schema_context=(
                request.schema_context if isinstance(request.schema_context, dict) else None
            ),
            conversation_summary=request.conversation_summary,
            session_state=request.session_state,
        )
        hypothesis = self._normalize_explicit_comparison(
            question=request.question,
            hypothesis=hypothesis,
        )
        hypothesis = self._normalize_persona_question(
            question=request.question,
            hypothesis=hypothesis,
        )
        hypothesis = self._normalize_campaign_collection_summary(
            question=request.question,
            hypothesis=hypothesis,
        )
        hypothesis = self._apply_entity_resolution(
            question=request.question,
            hypothesis=hypothesis,
        )
        hypothesis = self._apply_context_resolution(
            question=request.question,
            hypothesis=hypothesis,
        )
        hypothesis = self._normalize_campaign_ranking_with_shopping(
            question=request.question,
            hypothesis=hypothesis,
        )
        hypothesis = self._normalize_multi_metric_query(
            hypothesis=hypothesis,
            semantic_resolution=semantic_resolution,
        )
        hypothesis = self._normalize_sales_date_range_question(
            question=request.question,
            hypothesis=hypothesis,
        )
        hypothesis = self._normalize_explicit_ranking_limit(
            hypothesis=hypothesis,
            semantic_resolution=semantic_resolution,
        )
        analytical_plan = self._analytical_planner.build(
            hypothesis=hypothesis,
            knowledge_context=knowledge_context,
        )
        execution_plan = self._execution_plan_builder.build(analytical_plan)
        optimized_plan = self._optimizer.optimize(execution_plan)
        validation = self._validator.validate(optimized_plan)
        warnings = self._warnings(
            hypothesis_warnings=hypothesis.warnings,
            analytical_warnings=analytical_plan.warnings,
            validation_warnings=validation.warnings,
            execution_warnings=optimized_plan.warnings,
        )

        return CompilerResponse(
            question=request.question,
            hypothesis=hypothesis,
            analytical_plan=analytical_plan,
            execution_plan=optimized_plan,
            warnings=warnings,
            status="draft_created" if not warnings else "completed_with_warnings",
        )

    def _normalize_persona_question(
        self,
        *,
        question: str,
        hypothesis: AnalyticalHypothesis,
    ) -> AnalyticalHypothesis:
        normalized = self._context_resolver._normalize_text(question)
        if not re.search(r"\bpersona\b|\bperfil\s+(?:do\s+)?publico\b", normalized):
            return hypothesis

        has_comparison_term = bool(
            re.search(r"\b(comparativo|comparar|compare|entre|quadro)\b", normalized),
        )
        has_plural_shoppings = bool(
            re.search(r"\b(shoppings|empreendimentos)\b", normalized),
        )
        is_comparison = has_comparison_term and has_plural_shoppings

        warnings = [
            warning
            for warning in hypothesis.warnings
            if warning
            not in {
                "Nenhuma métrica identificada.",
                "Nenhuma entidade de negócio identificada.",
            }
        ]
        return hypothesis.model_copy(
            update={
                "analysis_type": "persona_comparison" if is_comparison else "persona",
                "business_entity": "empreendimento" if is_comparison else "genero",
                "metric": "clientes_unicos",
                "metrics": ["clientes_unicos"],
                "dimensions": ["genero", "faixa_etaria"],
                "warnings": warnings,
            },
        )

    def _build_hypothesis(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution | None,
        knowledge_context: KnowledgeContext | None,
        schema_context: dict[str, object] | None,
        conversation_summary: str = "",
        session_state: dict[str, object] | None = None,
    ) -> AnalyticalHypothesis:
        if self._reasoning_provider is not None:
            reasoning_result = self._reasoning_provider.generate_hypothesis(
                ReasoningContext(
                    question=question,
                    semantic_resolution=semantic_resolution,
                    knowledge_context=knowledge_context,
                    schema_context=schema_context,
                    conversation_summary=conversation_summary,
                    session_state=session_state or {},
                ),
            )
            if reasoning_result.success and reasoning_result.hypothesis is not None:
                return reasoning_result.hypothesis

            logger.warning(
                "ReasoningProvider failed; using deterministic fallback. "
                "provider=%s model=%s warnings=%s diagnostic=%s",
                reasoning_result.provider,
                reasoning_result.model,
                reasoning_result.warnings,
                (reasoning_result.raw_response or "unavailable")[:500],
            )
            return self._fallback_hypothesis(
                question=question,
                semantic_resolution=semantic_resolution,
                knowledge_context=knowledge_context,
            )

        return self._fallback_hypothesis(
            question=question,
            semantic_resolution=semantic_resolution,
            knowledge_context=knowledge_context,
        )

    def _normalize_explicit_comparison(
        self,
        *,
        question: str,
        hypothesis: AnalyticalHypothesis,
    ) -> AnalyticalHypothesis:
        normalized = self._context_resolver._normalize_text(question)
        patterns = (
            r"\bcomparar\b",
            r"\bcompare\b",
            r"\bcomparativ[oa]s?\b",
            r"\bversus\b",
            r"\bvs\b",
            r"\bcontra\b",
            r"\bem relacao a\b",
        )
        if not any(re.search(pattern, normalized) for pattern in patterns):
            return hypothesis

        return hypothesis.model_copy(update={"analysis_type": "comparison"})

    def _normalize_campaign_collection_summary(
        self,
        *,
        question: str,
        hypothesis: AnalyticalHypothesis,
    ) -> AnalyticalHypothesis:
        normalized = self._context_resolver._normalize_text(question)
        has_summary_request = bool(
            re.search(r"\b(resumo|resuma|resumir|detalhe|detalhar)\b", normalized),
        )
        has_plural_campaigns = bool(
            re.search(r"\b(campanhas|promocoes)\b", normalized),
        )
        if not (has_summary_request and has_plural_campaigns):
            return hypothesis

        return hypothesis.model_copy(
            update={
                "analysis_type": "comparison",
                "business_entity": hypothesis.business_entity or "promocao",
            },
        )

    def _normalize_campaign_ranking_with_shopping(
        self,
        *,
        question: str,
        hypothesis: AnalyticalHypothesis,
    ) -> AnalyticalHypothesis:
        normalized = self._context_resolver._normalize_text(question)
        asks_for_campaign_ranking = (
            hypothesis.analysis_type == "ranking"
            and hypothesis.business_entity == "promocao"
            and bool(re.search(r"\b(campanha|promocao)\b", normalized))
        )
        asks_for_shopping = bool(
            re.search(
                r"\b(?:qual|que|em qual|em que)\s+(?:foi\s+o\s+)?(?:shopping|empreendimento)\b",
                normalized,
            )
            or re.search(r"\b(?:shopping|empreendimento)\s+(?:ocorreu|aconteceu)\b", normalized)
        )
        if not (asks_for_campaign_ranking and asks_for_shopping):
            return hypothesis

        return hypothesis.model_copy(
            update={"dimensions": ["nm_promocao", "nm_empreendimento"]},
        )

    def _fallback_hypothesis(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution | None,
        knowledge_context: KnowledgeContext | None,
    ) -> AnalyticalHypothesis:
        return self._hypothesis_builder.build(
            question=question,
            semantic_resolution=semantic_resolution,
            knowledge_context=knowledge_context,
        )

    def _apply_entity_resolution(
        self,
        *,
        question: str,
        hypothesis: AnalyticalHypothesis,
    ) -> AnalyticalHypothesis:
        if hypothesis.analysis_type == "comparison":
            return self._apply_comparison_entity_resolution(
                question=question,
                hypothesis=hypothesis,
            )

        resolution = self._entity_resolver.resolve_many(question)
        if not resolution.matches:
            return hypothesis

        matches = resolution.matches
        normalized_question = self._context_resolver._normalize_text(question)
        has_shopping_match = any(match.entity_type == "empreendimento" for match in matches)
        explicitly_mentions_campaign = bool(
            re.search(r"\b(campanha|campanhas|promocao|promocoes)\b", normalized_question),
        )
        if (
            hypothesis.analysis_type == "persona"
            and has_shopping_match
            and not explicitly_mentions_campaign
        ):
            matches = [match for match in matches if match.entity_type != "promocao"]
        if hypothesis.analysis_type == "list_distinct" and has_shopping_match:
            matches = [match for match in matches if match.entity_type != "promocao"]

        shopping_matches = [
            match for match in matches if match.entity_type == "empreendimento"
        ]
        if len(shopping_matches) > 1:
            explicit_shoppings = [
                match
                for match in shopping_matches
                if self._context_resolver._normalize_text(match.value) in normalized_question
            ]
            selected_shopping = (
                max(explicit_shoppings, key=lambda match: len(match.value))
                if explicit_shoppings
                else max(shopping_matches, key=lambda match: match.confidence)
            )
            matches = [
                match
                for match in matches
                if match.entity_type != "empreendimento" or match == selected_shopping
            ]

        if resolution.is_ambiguous:
            warning = resolution.ambiguity_message or "Entidade ambígua."
            return hypothesis.model_copy(
                update={"warnings": [*hypothesis.warnings, warning]},
            )

        filters = [
            *hypothesis.filters,
            *[self._entity_filter(match) for match in matches],
        ]
        business_entity = hypothesis.business_entity or matches[0].entity_type
        warnings = [
            warning
            for warning in hypothesis.warnings
            if warning != "Nenhuma entidade de negócio identificada."
        ]

        return hypothesis.model_copy(
            update={
                "business_entity": business_entity,
                "filters": filters,
                "warnings": warnings,
            },
        )

    def _entity_filter(self, match: EntityMatch) -> dict[str, object]:
        return {
            "type": "filter",
            "field": match.field,
            "operator": "equals",
            "value": match.value,
            "source": "entity_resolution",
            "confidence": match.confidence,
        }

    def _apply_context_resolution(
        self,
        *,
        question: str,
        hypothesis: AnalyticalHypothesis,
    ) -> AnalyticalHypothesis:
        if hypothesis.analysis_type == "comparison":
            return hypothesis

        resolved_context = self._context_resolver.resolve(question)
        if not self._has_context(resolved_context):
            return hypothesis

        filters = [
            *hypothesis.filters,
            *[
                {
                    "type": "filter",
                    "field": resolved_filter.field,
                    "operator": resolved_filter.operator,
                    "value": resolved_filter.value,
                }
                for resolved_filter in resolved_context.filters
            ],
        ]
        if (
            (resolved_context.intent or hypothesis.analysis_type) == "ranking"
            and not any(filter_item.get("type") == "limit" for filter_item in filters)
        ):
            filters.append({"type": "limit", "value": self._default_ranking_limit(question)})

        dimensions = [dimension.field for dimension in resolved_context.dimensions]
        metric = resolved_context.metrics[0].name if resolved_context.metrics else hypothesis.metric
        metric_source = hypothesis.metric_source
        if resolved_context.metrics and metric_source != "business_default":
            metric_source = "explicit"

        business_entity = (
            resolved_context.dimensions[0].label
            if resolved_context.dimensions and resolved_context.dimensions[0].label is not None
            else hypothesis.business_entity
        )
        warnings = [*hypothesis.warnings, *resolved_context.warnings]
        if resolved_context.metrics:
            warnings = [
                warning for warning in warnings if warning != "Nenhuma métrica identificada."
            ]
        if resolved_context.dimensions:
            warnings = [
                warning
                for warning in warnings
                if warning != "Nenhuma entidade de negócio identificada."
            ]

        return hypothesis.model_copy(
            update={
                "analysis_type": resolved_context.intent or hypothesis.analysis_type,
                "business_entity": business_entity,
                "metric": metric,
                "metric_source": metric_source,
                "dimensions": dimensions or hypothesis.dimensions,
                "filters": self._deduplicate_filters(filters),
                "warnings": warnings,
            },
        )

    def _default_ranking_limit(self, question: str) -> int:
        normalized = self._context_resolver._normalize_text(question)
        singular_patterns = (
            r"\bqual\s+(foi\s+a\s+|foi\s+o\s+)?loja\b",
            r"\bqual\s+(foi\s+o\s+)?segmento\b",
            r"\bqual\s+(foi\s+o\s+)?bairro\b",
            r"\bqual\s+(foi\s+a\s+)?cidade\b",
            r"\bqual\s+(foi\s+a\s+|foi\s+o\s+)?campanha\b",
        )
        if any(re.search(pattern, normalized) for pattern in singular_patterns):
            return 1

        return 10

    def _normalize_explicit_ranking_limit(
        self,
        *,
        hypothesis: AnalyticalHypothesis,
        semantic_resolution: SemanticResolution | None,
    ) -> AnalyticalHypothesis:
        if hypothesis.analysis_type != "ranking" or semantic_resolution is None:
            return hypothesis

        requested_limit = next(
            (
                parameter.value
                for parameter in semantic_resolution.parameters
                if parameter.type == "limit" and isinstance(parameter.value, int)
            ),
            None,
        )
        if requested_limit is None:
            return hypothesis

        filters = [
            filter_item
            for filter_item in hypothesis.filters
            if filter_item.get("type") != "limit"
        ]
        filters.append({"type": "limit", "value": requested_limit})
        return hypothesis.model_copy(update={"filters": filters})

    def _normalize_sales_date_range_question(
        self,
        *,
        question: str,
        hypothesis: AnalyticalHypothesis,
    ) -> AnalyticalHypothesis:
        normalized = self._context_resolver._normalize_text(question)
        patterns = (
            r"\bvendas?\s+a\s+partir\s+de\s+que\s+data\b",
            r"\ba\s+partir\s+de\s+que\s+data.*\bvendas?\b",
            r"\bdesde\s+quando.*\b(vendas?|compras?|dados)\b",
            r"\bqual\s+(?:e\s+)?o\s+periodo.*\b(vendas?|compras?|dados)\b",
            r"\bprimeira\s+(venda|compra)\b",
        )
        if not any(re.search(pattern, normalized) for pattern in patterns):
            return hypothesis

        warnings = [
            warning
            for warning in hypothesis.warnings
            if warning
            not in {
                "Nenhuma métrica identificada.",
                "Nenhuma entidade de negócio identificada.",
            }
        ]
        return hypothesis.model_copy(
            update={
                "goal": "identificar o período disponível de vendas",
                "analysis_type": "sales_date_range",
                "business_entity": None,
                "metric": "primeira_venda",
                "metrics": ["primeira_venda", "ultima_venda"],
                "metric_source": "business_rule",
                "dimensions": [],
                "warnings": warnings,
            },
        )

    def _normalize_multi_metric_query(
        self,
        *,
        hypothesis: AnalyticalHypothesis,
        semantic_resolution: SemanticResolution | None,
    ) -> AnalyticalHypothesis:
        if hypothesis.analysis_type in {
            "comparison",
            "ranking",
            "summary",
            "campaign_detail",
            "campaign_summary",
            "sales_date_range",
        }:
            return hypothesis
        semantic_metrics = (
            semantic_resolution.interpretation.metrics
            if semantic_resolution is not None
            and semantic_resolution.interpretation is not None
            else []
        )
        metrics = semantic_metrics or hypothesis.metrics
        if len(metrics) < 2:
            return hypothesis

        warnings = [
            warning
            for warning in hypothesis.warnings
            if warning
            not in {
                "Nenhuma métrica identificada.",
                "Nenhuma entidade de negócio identificada.",
            }
        ]
        return hypothesis.model_copy(
            update={
                "analysis_type": "metric_query",
                "metric": metrics[0],
                "metrics": metrics,
                "warnings": warnings,
            },
        )

    def _has_context(self, resolved_context: ResolvedContext) -> bool:
        return bool(
            resolved_context.filters
            or resolved_context.dimensions
            or resolved_context.metrics
            or resolved_context.intent
            or resolved_context.warnings
        )

    def _deduplicate_filters(self, filters: list[dict[str, object]]) -> list[dict[str, object]]:
        deduplicated: list[dict[str, object]] = []
        seen: set[tuple[object, object, object]] = set()
        for filter_item in filters:
            key = (
                filter_item.get("field"),
                filter_item.get("operator"),
                str(filter_item.get("value")),
            )
            if key in seen:
                continue

            deduplicated.append(filter_item)
            seen.add(key)

        return deduplicated

    def _apply_comparison_entity_resolution(
        self,
        *,
        question: str,
        hypothesis: AnalyticalHypothesis,
    ) -> AnalyticalHypothesis:
        resolution = self._entity_resolver.resolve_many(question)
        if resolution.is_ambiguous:
            warning = resolution.ambiguity_message or "Entidade ambígua."
            return hypothesis.model_copy(
                update={"warnings": [*hypothesis.warnings, warning]},
            )

        if not resolution.matches:
            return hypothesis

        normalized_question = self._context_resolver._normalize_text(question)
        shopping_matches = [
            match for match in resolution.matches if match.entity_type == "empreendimento"
        ]
        compares_campaign_collection = bool(
            re.search(r"\b(campanhas|promocoes)\b", normalized_question)
            and re.search(r"\b(quadro|comparativo|comparar|compare)\b", normalized_question)
        )
        if compares_campaign_collection and shopping_matches:
            explicit_shoppings = [
                match
                for match in shopping_matches
                if self._context_resolver._normalize_text(match.value) in normalized_question
            ]
            selected_shopping = (
                max(explicit_shoppings, key=lambda match: len(match.value))
                if explicit_shoppings
                else max(shopping_matches, key=lambda match: match.confidence)
            )
            shopping_filter = self._entity_filter(selected_shopping)
            filters = self._deduplicate_filters([*hypothesis.filters, shopping_filter])
            warnings = [
                warning
                for warning in hypothesis.warnings
                if warning
                not in {
                    "Nenhuma entidade de negócio identificada.",
                    "Nenhuma métrica identificada.",
                }
            ]
            return hypothesis.model_copy(
                update={
                    "business_entity": "promocao",
                    "filters": filters,
                    "comparison_entities": [],
                    "warnings": warnings,
                },
            )

        if len(resolution.matches) < 2:
            return hypothesis.model_copy(
                update={
                    "warnings": [
                        *hypothesis.warnings,
                        "Não identifiquei duas entidades para comparação.",
                    ],
                },
            )

        field_names = {match.field for match in resolution.matches}
        if len(field_names) > 1:
            return hypothesis.model_copy(
                update={
                    "warnings": [
                        *hypothesis.warnings,
                        "A comparação contém entidades de campos diferentes.",
                    ],
                },
            )

        comparison_entities = [
            {
                "field": match.field,
                "value": match.value,
                "label": match.value,
                "entity_type": match.entity_type,
                "confidence": match.confidence,
            }
            for match in resolution.matches
        ]
        comparison_field = resolution.matches[0].field
        filters = [
            filter_item
            for filter_item in hypothesis.filters
            if not (
                filter_item.get("type") == "filter"
                and filter_item.get("field") == comparison_field
            )
        ]
        business_entity = hypothesis.business_entity or resolution.matches[0].entity_type
        warnings = [
            warning
            for warning in hypothesis.warnings
            if warning
            not in {
                "Nenhuma entidade de negócio identificada.",
                "Nenhuma métrica identificada.",
            }
        ]

        return hypothesis.model_copy(
            update={
                "business_entity": business_entity,
                "filters": filters,
                "comparison_entities": comparison_entities,
                "warnings": warnings,
            },
        )

    def _warnings(
        self,
        *,
        hypothesis_warnings: list[str],
        analytical_warnings: list[str],
        validation_warnings: list[str],
        execution_warnings: list[str],
    ) -> list[str]:
        warnings: list[str] = []
        seen: set[str] = set()

        for warning in [
            *hypothesis_warnings,
            *analytical_warnings,
            *validation_warnings,
            *execution_warnings,
        ]:
            if warning in seen:
                continue

            warnings.append(warning)
            seen.add(warning)

        return warnings

import logging

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
        )
        hypothesis = self._apply_entity_resolution(
            question=request.question,
            hypothesis=hypothesis,
        )
        hypothesis = self._apply_context_resolution(
            question=request.question,
            hypothesis=hypothesis,
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

    def _build_hypothesis(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution | None,
        knowledge_context: KnowledgeContext | None,
        schema_context: dict[str, object] | None,
    ) -> AnalyticalHypothesis:
        if self._reasoning_provider is not None:
            reasoning_result = self._reasoning_provider.generate_hypothesis(
                ReasoningContext(
                    question=question,
                    semantic_resolution=semantic_resolution,
                    knowledge_context=knowledge_context,
                    schema_context=schema_context,
                ),
            )
            if reasoning_result.success and reasoning_result.hypothesis is not None:
                return reasoning_result.hypothesis

            logger.warning(
                "ReasoningProvider failed; using deterministic fallback. "
                "provider=%s model=%s warnings=%s",
                reasoning_result.provider,
                reasoning_result.model,
                reasoning_result.warnings,
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

        if resolution.is_ambiguous:
            warning = resolution.ambiguity_message or "Entidade ambígua."
            return hypothesis.model_copy(
                update={"warnings": [*hypothesis.warnings, warning]},
            )

        filters = [
            *hypothesis.filters,
            *[self._entity_filter(match) for match in resolution.matches],
        ]
        business_entity = hypothesis.business_entity or resolution.matches[0].entity_type
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
            filters.append({"type": "limit", "value": 1})

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

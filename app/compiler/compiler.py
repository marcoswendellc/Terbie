from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import AnalyticalHypothesis, CompilerRequest, CompilerResponse
from app.knowledge.models import KnowledgeContext
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.reasoning.base import BaseReasoningProvider
from app.reasoning.models import ReasoningContext
from app.semantic.models import SemanticResolution


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
    ) -> None:
        self._hypothesis_builder = hypothesis_builder
        self._analytical_planner = analytical_planner
        self._execution_plan_builder = execution_plan_builder
        self._validator = validator
        self._optimizer = optimizer
        self._reasoning_provider = reasoning_provider

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
        fallback_warning = "ReasoningProvider falhou; fallback determinístico utilizado."
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

            hypothesis = self._fallback_hypothesis(
                question=question,
                semantic_resolution=semantic_resolution,
                knowledge_context=knowledge_context,
            )
            return hypothesis.model_copy(
                update={"warnings": [*hypothesis.warnings, fallback_warning]},
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

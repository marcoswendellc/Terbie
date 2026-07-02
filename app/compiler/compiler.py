from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest, CompilerResponse
from app.knowledge.models import KnowledgeContext
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
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
    ) -> None:
        self._hypothesis_builder = hypothesis_builder
        self._analytical_planner = analytical_planner
        self._execution_plan_builder = execution_plan_builder
        self._validator = validator
        self._optimizer = optimizer

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

        hypothesis = self._hypothesis_builder.build(
            question=request.question,
            semantic_resolution=semantic_resolution,
            knowledge_context=knowledge_context,
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

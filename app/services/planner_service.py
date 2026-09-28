from typing import Any

from app.catalog.data_catalog import DataCatalog
from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest, CompilerResponse
from app.knowledge.models import KnowledgeContext
from app.planner.models import PlannerResponse, PlanValidationResult
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.semantic.models import SemanticResolution


class PlannerService:
    """Application service that creates, validates, and optimizes draft plans."""

    def __init__(self, compiler: TerbieCompiler) -> None:
        self._compiler = compiler

    @classmethod
    def deterministic(cls) -> "PlannerService":
        """Local preflight uses the canonical compiler without another model call."""
        return cls(
            compiler=TerbieCompiler(
                hypothesis_builder=HypothesisBuilder(),
                analytical_planner=AnalyticalPlanner(),
                execution_plan_builder=ExecutionPlanBuilder(),
                validator=PlanValidator(),
                optimizer=PlanOptimizer(),
            )
        )

    def create_draft_plan(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution,
        schema: dict[str, Any] | None = None,
        data_catalog: DataCatalog | None = None,
        knowledge_context: KnowledgeContext | None = None,
        conversation_summary: str = "",
        session_state: dict[str, Any] | None = None,
    ) -> PlannerResponse:
        compiler_response = self.create_compiler_draft(
            question=question,
            semantic_resolution=semantic_resolution,
            schema=schema,
            knowledge_context=knowledge_context,
            conversation_summary=conversation_summary,
            session_state=session_state,
        )
        _ = data_catalog

        return PlannerResponse(
            question=compiler_response.question,
            semantic_resolution=semantic_resolution,
            plan=compiler_response.execution_plan,
            validation=PlanValidationResult(
                is_valid=not compiler_response.warnings,
                warnings=compiler_response.warnings,
            ),
        )

    def create_compiler_draft(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution,
        schema: dict[str, Any] | None = None,
        knowledge_context: KnowledgeContext | None = None,
        conversation_summary: str = "",
        session_state: dict[str, Any] | None = None,
    ) -> CompilerResponse:
        return self._compiler.compile(
            CompilerRequest(
                question=question,
                semantic_resolution=semantic_resolution,
                knowledge_context=knowledge_context,
                schema_context=schema,
                conversation_summary=conversation_summary,
                session_state=session_state or {},
            ),
        )

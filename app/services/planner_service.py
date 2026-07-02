from typing import Any

from app.catalog.data_catalog import DataCatalog
from app.compiler.compiler import TerbieCompiler
from app.compiler.models import CompilerRequest, CompilerResponse
from app.knowledge.models import KnowledgeContext
from app.planner.models import PlannerResponse, PlanValidationResult
from app.semantic.models import SemanticResolution


class PlannerService:
    """Application service that creates, validates, and optimizes draft plans."""

    def __init__(self, compiler: TerbieCompiler) -> None:
        self._compiler = compiler

    def create_draft_plan(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution,
        schema: dict[str, Any] | None = None,
        data_catalog: DataCatalog | None = None,
        knowledge_context: KnowledgeContext | None = None,
    ) -> PlannerResponse:
        compiler_response = self.create_compiler_draft(
            question=question,
            semantic_resolution=semantic_resolution,
            schema=schema,
            knowledge_context=knowledge_context,
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
    ) -> CompilerResponse:
        return self._compiler.compile(
            CompilerRequest(
                question=question,
                semantic_resolution=semantic_resolution,
                knowledge_context=knowledge_context,
                schema_context=schema,
            ),
        )

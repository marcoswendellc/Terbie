from typing import Any

from app.catalog.data_catalog import DataCatalog
from app.knowledge.models import KnowledgeContext
from app.planner.context_composer import PlannerContextComposer
from app.planner.models import PlannerResponse
from app.planner.optimizer import PlanOptimizer
from app.planner.parser import PlanParser
from app.planner.validator import PlanValidator
from app.reasoning.base import BaseReasoningProvider
from app.semantic.models import SemanticResolution


class PlannerCompiler:
    """Central Planner coordinator based on specification-driven reasoning contracts."""

    def __init__(
        self,
        context_composer: PlannerContextComposer,
        reasoning_provider: BaseReasoningProvider,
        parser: PlanParser,
        validator: PlanValidator,
        optimizer: PlanOptimizer,
    ) -> None:
        self._context_composer = context_composer
        self._reasoning_provider = reasoning_provider
        self._parser = parser
        self._validator = validator
        self._optimizer = optimizer

    def compile(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution,
        schema: dict[str, Any] | None = None,
        data_catalog: DataCatalog | None = None,
        knowledge_context: KnowledgeContext | None = None,
    ) -> PlannerResponse:
        context = self._context_composer.compose(
            question=question,
            semantic_resolution=semantic_resolution,
            schema=schema,
            data_catalog=data_catalog,
            knowledge_context=knowledge_context,
        )
        reasoning_result = self._reasoning_provider.generate_execution_plan(context)
        parsed_plan = self._parser.parse(reasoning_result.execution_plan.model_dump(mode="json"))
        optimized_plan = self._optimizer.optimize(parsed_plan)
        validation = self._validator.validate(optimized_plan)

        return PlannerResponse(
            question=question,
            semantic_resolution=semantic_resolution,
            plan=optimized_plan,
            validation=validation,
        )

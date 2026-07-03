from pydantic import BaseModel, ConfigDict

from app.intent_guard.intent_guard import IntentGuard
from app.knowledge.knowledge_service import KnowledgeService
from app.planner.models import ExecutionPlan
from app.semantic.models import SemanticResolution
from app.services.planner_service import PlannerService
from app.services.semantic_service import SemanticService


class TerbieDraftResponse(BaseModel):
    question: str
    semantic_resolution: SemanticResolution | None = None
    draft_plan: ExecutionPlan | None = None
    status: str
    response: str | None = None

    model_config = ConfigDict(frozen=True)


class TerbieOrchestrator:
    """Coordinates semantic resolution and draft planning without execution."""

    def __init__(
        self,
        semantic_service: SemanticService,
        planner_service: PlannerService,
        knowledge_service: KnowledgeService,
        intent_guard: IntentGuard | None = None,
    ) -> None:
        self._semantic_service = semantic_service
        self._planner_service = planner_service
        self._knowledge_service = knowledge_service
        self._intent_guard = intent_guard or IntentGuard()

    def create_draft(self, *, question: str) -> TerbieDraftResponse:
        intent_guard_result = self._intent_guard.evaluate(question)
        if not intent_guard_result.is_analytical:
            return TerbieDraftResponse(
                question=question,
                status="out_of_scope",
                response=intent_guard_result.response,
            )

        semantic_resolution = self._semantic_service.resolve(question=question)
        planner_response = self._planner_service.create_draft_plan(
            question=question,
            semantic_resolution=semantic_resolution,
            knowledge_context=self._knowledge_service.get_context(),
        )

        return TerbieDraftResponse(
            question=question,
            semantic_resolution=semantic_resolution,
            draft_plan=planner_response.plan,
            status="draft_created",
        )

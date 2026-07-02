from pydantic import BaseModel, ConfigDict

from app.knowledge.knowledge_service import KnowledgeService
from app.planner.models import ExecutionPlan
from app.semantic.models import SemanticResolution
from app.services.planner_service import PlannerService
from app.services.semantic_service import SemanticService


class TerbieDraftResponse(BaseModel):
    question: str
    semantic_resolution: SemanticResolution
    draft_plan: ExecutionPlan
    status: str

    model_config = ConfigDict(frozen=True)


class TerbieOrchestrator:
    """Coordinates semantic resolution and draft planning without execution."""

    def __init__(
        self,
        semantic_service: SemanticService,
        planner_service: PlannerService,
        knowledge_service: KnowledgeService,
    ) -> None:
        self._semantic_service = semantic_service
        self._planner_service = planner_service
        self._knowledge_service = knowledge_service

    def create_draft(self, *, question: str) -> TerbieDraftResponse:
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

from pydantic import BaseModel, ConfigDict, Field

from app.intent_guard.intent_guard import IntentGuard
from app.knowledge.knowledge_service import KnowledgeService
from app.memory.conversation import ConversationMemoryService
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
    session_id: str | None = None
    rewritten_question: str | None = None
    session_state: dict = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class TerbieOrchestrator:
    """Coordinates semantic resolution and draft planning without execution."""

    def __init__(
        self,
        semantic_service: SemanticService,
        planner_service: PlannerService,
        knowledge_service: KnowledgeService,
        intent_guard: IntentGuard | None = None,
        conversation_memory: ConversationMemoryService | None = None,
    ) -> None:
        self._semantic_service = semantic_service
        self._planner_service = planner_service
        self._knowledge_service = knowledge_service
        self._intent_guard = intent_guard or IntentGuard()
        self._conversation_memory = conversation_memory

    def create_draft(self, *, question: str, session_id: str | None = None) -> TerbieDraftResponse:
        original_question = question
        memory_context = None
        if self._conversation_memory is not None and session_id is not None:
            memory_context = self._conversation_memory.contextualize(
                session_id=session_id, question=question
            )
            if memory_context.clarification:
                self._conversation_memory.record(
                    session_id=session_id,
                    context=memory_context,
                    answer=memory_context.clarification,
                )
                return TerbieDraftResponse(
                    question=original_question,
                    status="clarification_required",
                    response=memory_context.clarification,
                    session_id=session_id,
                    session_state=memory_context.state.model_dump(mode="json"),
                )
            question = memory_context.rewritten_question
        intent_guard_result = self._intent_guard.evaluate(question)
        if intent_guard_result.should_stop:
            return TerbieDraftResponse(
                question=question,
                status=intent_guard_result.intent,
                response=intent_guard_result.response,
            )

        semantic_resolution = self._semantic_service.resolve(question=question)
        planner_response = self._planner_service.create_draft_plan(
            question=question,
            semantic_resolution=semantic_resolution,
            knowledge_context=self._knowledge_service.get_context(),
            conversation_summary=memory_context.summary if memory_context else "",
            session_state=memory_context.state.model_dump(mode="json") if memory_context else {},
        )

        return TerbieDraftResponse(
            question=original_question,
            semantic_resolution=semantic_resolution,
            draft_plan=planner_response.plan,
            status="draft_created",
            session_id=session_id,
            rewritten_question=question,
            session_state=memory_context.state.model_dump(mode="json") if memory_context else {},
        )

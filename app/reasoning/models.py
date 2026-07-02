from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.knowledge.models import KnowledgeContext
from app.planner.models import ExecutionPlan
from app.semantic.models import SemanticResolution

ReasoningRole = Literal["system", "user", "assistant"]


class ReasoningMessage(BaseModel):
    role: ReasoningRole
    content: str

    model_config = ConfigDict(frozen=True)


class ReasoningContext(BaseModel):
    question: str
    semantic_resolution: SemanticResolution
    schema_context: dict[str, Any] | None = Field(default=None, alias="schema")
    data_catalog: dict[str, Any] | None = None
    knowledge_context: KnowledgeContext | None = None
    messages: list[ReasoningMessage] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True, populate_by_name=True)


class ReasoningResult(BaseModel):
    execution_plan: ExecutionPlan
    messages: list[ReasoningMessage] = Field(default_factory=list)
    raw_output: dict[str, Any] | None = None

    model_config = ConfigDict(frozen=True)

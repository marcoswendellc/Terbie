from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.compiler.models import AnalyticalHypothesis
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
    semantic_resolution: SemanticResolution | None = None
    schema_context: dict[str, Any] | None = Field(default=None, alias="schema")
    catalog_context: dict[str, Any] | None = Field(default=None, alias="data_catalog")
    knowledge_context: KnowledgeContext | None = None
    messages: list[ReasoningMessage] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    @property
    def data_catalog(self) -> dict[str, Any] | None:
        return self.catalog_context


class ReasoningResult(BaseModel):
    hypothesis: AnalyticalHypothesis | None = None
    raw_response: str | None = None
    warnings: list[str] = Field(default_factory=list)
    provider: str
    model: str | None = None
    success: bool
    execution_plan: ExecutionPlan | None = None
    messages: list[ReasoningMessage] = Field(default_factory=list)
    raw_output: dict[str, Any] | None = None

    model_config = ConfigDict(frozen=True)

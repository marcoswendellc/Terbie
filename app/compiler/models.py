from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.planner.models import ExecutionPlan


class AnalysisItem(BaseModel):
    entity: str
    value: str
    context: dict[str, str] = Field(default_factory=dict)
    identifier: str | None = None

    model_config = ConfigDict(frozen=True)


class PresentationSpec(BaseModel):
    format: str = "narrative"
    percentages_by_default: bool = True

    model_config = ConfigDict(frozen=True)


class AnalyticalHypothesis(BaseModel):
    goal: str | None = None
    analysis_type: str | None = None
    business_entity: str | None = None
    metric: str | None = None
    metrics: list[str] = Field(default_factory=list)
    metric_source: str | None = None
    dimensions: list[str] = Field(default_factory=list)
    time_scope: str | None = None
    filters: list[dict[str, Any]] = Field(default_factory=list)
    comparison_entities: list[dict[str, Any]] = Field(default_factory=list)
    items: list[AnalysisItem] = Field(default_factory=list)
    presentation: PresentationSpec = Field(default_factory=PresentationSpec)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class AnalyticalPlan(BaseModel):
    intent: str | None = None
    entities: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    time_scope: str | None = None
    filters: list[dict[str, Any]] = Field(default_factory=list)
    comparison_entities: list[dict[str, Any]] = Field(default_factory=list)
    items: list[AnalysisItem] = Field(default_factory=list)
    presentation: PresentationSpec = Field(default_factory=PresentationSpec)
    required_operations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class CompilerRequest(BaseModel):
    question: str
    semantic_resolution: Any | None = None
    knowledge_context: Any | None = None
    schema_context: Any | None = None
    conversation_summary: str = ""
    session_state: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class CompilerResponse(BaseModel):
    question: str
    hypothesis: AnalyticalHypothesis
    analytical_plan: AnalyticalPlan
    execution_plan: ExecutionPlan
    warnings: list[str] = Field(default_factory=list)
    status: str

    model_config = ConfigDict(frozen=True)

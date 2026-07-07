from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.planner.models import ExecutionPlan


class AnalyticalHypothesis(BaseModel):
    goal: str | None = None
    analysis_type: str | None = None
    business_entity: str | None = None
    metric: str | None = None
    metric_source: str | None = None
    dimensions: list[str] = Field(default_factory=list)
    time_scope: str | None = None
    filters: list[dict[str, Any]] = Field(default_factory=list)
    comparison_entities: list[dict[str, Any]] = Field(default_factory=list)
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
    required_operations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class CompilerRequest(BaseModel):
    question: str
    semantic_resolution: Any | None = None
    knowledge_context: Any | None = None
    schema_context: Any | None = None

    model_config = ConfigDict(frozen=True)


class CompilerResponse(BaseModel):
    question: str
    hypothesis: AnalyticalHypothesis
    analytical_plan: AnalyticalPlan
    execution_plan: ExecutionPlan
    warnings: list[str] = Field(default_factory=list)
    status: str

    model_config = ConfigDict(frozen=True)

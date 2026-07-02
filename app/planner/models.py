from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.semantic.models import SemanticResolution


class PlannerRequest(BaseModel):
    question: str = Field(min_length=1)

    model_config = ConfigDict(frozen=True)


class PlanEntity(BaseModel):
    name: str

    model_config = ConfigDict(frozen=True)


class PlanMetric(BaseModel):
    name: str
    aggregation: str | None = None

    model_config = ConfigDict(frozen=True)


class PlanParameter(BaseModel):
    type: str
    value: Any

    model_config = ConfigDict(frozen=True)


class PlanOperation(BaseModel):
    type: str
    function: str | None = None
    field: str | None = None
    alias: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class ExecutionPlan(BaseModel):
    version: str = "1.0"
    intent: str | None = None
    entities: list[PlanEntity] = Field(default_factory=list)
    metrics: list[PlanMetric] = Field(default_factory=list)
    parameters: list[PlanParameter] = Field(default_factory=list)
    operations: list[PlanOperation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    is_executable: bool = False

    model_config = ConfigDict(frozen=True)


class PlanValidationResult(BaseModel):
    is_valid: bool
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class PlannerResponse(BaseModel):
    question: str
    semantic_resolution: SemanticResolution
    plan: ExecutionPlan
    validation: PlanValidationResult

    model_config = ConfigDict(frozen=True)

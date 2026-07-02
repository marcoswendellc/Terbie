from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.planner.models import ExecutionPlan


class LogicalPlanNode(BaseModel):
    id: str
    type: str
    inputs: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class LogicalQueryPlan(BaseModel):
    version: str = "1.0"
    source: str | None = None
    table: str | None = None
    nodes: list[LogicalPlanNode] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    is_valid: bool = False

    model_config = ConfigDict(frozen=True)


class LogicalPlanValidationResult(BaseModel):
    is_valid: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class QueryPlanDraftResponse(BaseModel):
    question: str
    execution_plan: ExecutionPlan
    logical_query_plan: LogicalQueryPlan
    validation: LogicalPlanValidationResult

    model_config = ConfigDict(frozen=True)

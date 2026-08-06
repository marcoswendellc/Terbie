from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.planner.models import ExecutionPlan


class QueryPlan(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    dimensions: list[str] = Field(default_factory=list)
    filters: list[dict[str, Any]] = Field(default_factory=list)
    order_by: str | None = None
    order: str | None = None
    top: int | None = None
    limit: int | None = None
    question: str
    execution_plan: ExecutionPlan = Field(exclude=True)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_ranking_size(self) -> "QueryPlan":
        if self.top != self.limit:
            raise ValueError("QueryPlan top and limit must have the same value")
        return self


class MultiQueryPlan(BaseModel):
    question: str
    plans: list[QueryPlan] = Field(min_length=1)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "MultiQueryPlan":
        plan_ids = [plan.id for plan in self.plans]
        if len(plan_ids) != len(set(plan_ids)):
            raise ValueError("MultiQueryPlan plan ids must be unique")
        return self


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

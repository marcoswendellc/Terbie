from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NarratorRequest(BaseModel):
    question: str
    execution_result: Any
    semantic_resolution: Any | None = None
    execution_plan: Any | None = None
    insight_result: Any | None = None

    model_config = ConfigDict(frozen=True)


class NarrativeContext(BaseModel):
    question: str
    rows_returned: int
    data: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    top_row: dict[str, Any] | None = None
    metric_columns: list[str] = Field(default_factory=list)
    dimension_columns: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    intent: str | None = None
    insight_result: Any | None = None

    model_config = ConfigDict(frozen=True)


class NarratorResponse(BaseModel):
    answer: str
    summary: str | None = None
    highlights: list[str] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class ExecuteResponse(BaseModel):
    question: str
    answer: str
    highlights: list[str] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    data: list[dict[str, Any]]
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResolvedFilter(BaseModel):
    concept: str
    field: str
    operator: str
    value: Any
    label: str | None = None
    confidence: float = 1.0

    model_config = ConfigDict(frozen=True)


class ResolvedDimension(BaseModel):
    concept: str
    field: str
    label: str | None = None

    model_config = ConfigDict(frozen=True)


class ResolvedMetric(BaseModel):
    name: str
    formula: str | None = None
    aggregation: str | None = None
    field: str | None = None

    model_config = ConfigDict(frozen=True)


class ResolvedContext(BaseModel):
    filters: list[ResolvedFilter] = Field(default_factory=list)
    dimensions: list[ResolvedDimension] = Field(default_factory=list)
    metrics: list[ResolvedMetric] = Field(default_factory=list)
    intent: str | None = None
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Insight(BaseModel):
    id: str
    type: str
    title: str
    description: str
    severity: str = "info"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metric: str | None = None
    entity: str | None = None
    value: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class InsightResult(BaseModel):
    insights: list[Insight] = Field(default_factory=list)
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)

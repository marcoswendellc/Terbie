from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MetricSource = Literal["explicit", "business_default"]


class MetricResolutionResult(BaseModel):
    metric: str | None = None
    source: MetricSource | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_term: str | None = None

    model_config = ConfigDict(frozen=True)

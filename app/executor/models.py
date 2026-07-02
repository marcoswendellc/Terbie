from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExecutionRequest(BaseModel):
    question: str = Field(min_length=1)

    model_config = ConfigDict(frozen=True)


class ExecutionResult(BaseModel):
    data: list[dict[str, Any]]
    metadata: dict[str, Any] = Field(default_factory=dict)
    statistics: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    execution_time: float
    rows_returned: int

    model_config = ConfigDict(frozen=True)

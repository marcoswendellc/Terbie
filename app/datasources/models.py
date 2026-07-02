from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DataSourceConfig(BaseModel):
    name: str
    type: str
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class DataSourceInfo(BaseModel):
    name: str
    type: str
    tables: list[str]
    healthy: bool

    model_config = ConfigDict(frozen=True)


class DataSourceHealth(BaseModel):
    name: str
    healthy: bool
    message: str | None = None

    model_config = ConfigDict(frozen=True)

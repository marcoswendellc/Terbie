from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ColumnDataType = Literal["string", "number", "datetime", "boolean"]
ComparableValue = str | int | float | bool | datetime | None


class ColumnSchema(BaseModel):
    name: str
    data_type: ColumnDataType
    nullable: bool
    null_count: int = Field(ge=0)
    unique_count: int = Field(ge=0)
    min_value: ComparableValue = None
    max_value: ComparableValue = None
    examples: list[Any] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class TableSchema(BaseModel):
    name: str
    row_count: int = Field(ge=0)
    columns: list[ColumnSchema]

    model_config = ConfigDict(frozen=True)


class DataCatalogEntry(BaseModel):
    table_name: str
    table_schema: TableSchema
    source: str
    datasource_name: str | None = None
    loaded_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))

    model_config = ConfigDict(frozen=True)

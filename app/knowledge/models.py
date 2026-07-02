from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BusinessEntity(BaseModel):
    name: str
    fields: list[str] = Field(default_factory=list)
    description: str | None = None

    model_config = ConfigDict(frozen=True)


class BusinessMetric(BaseModel):
    name: str
    column: str | None = None
    aggregation: str | None = None
    formula: str | None = None
    synonyms: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class BusinessDimension(BaseModel):
    name: str
    column: str | None = None
    key: str | None = None
    derived_from: str | None = None
    derivation_rule: str | None = None

    model_config = ConfigDict(frozen=True)


class BusinessRule(BaseModel):
    code: str
    description: str
    fields: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class BusinessHierarchy(BaseModel):
    name: str
    levels: list[str]

    model_config = ConfigDict(frozen=True)


class BusinessCalendar(BaseModel):
    name: str
    primary_field: str | None = None
    fields: list[str] = Field(default_factory=list)
    used_for: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class BusinessTaxonomy(BaseModel):
    name: str
    source_field: str
    rules: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class KnowledgeContext(BaseModel):
    entities: list[BusinessEntity] = Field(default_factory=list)
    metrics: list[BusinessMetric] = Field(default_factory=list)
    dimensions: list[BusinessDimension] = Field(default_factory=list)
    rules: list[BusinessRule] = Field(default_factory=list)
    hierarchies: list[BusinessHierarchy] = Field(default_factory=list)
    calendars: list[BusinessCalendar] = Field(default_factory=list)
    taxonomies: list[BusinessTaxonomy] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)

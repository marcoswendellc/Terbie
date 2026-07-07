from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SemanticTermType = Literal["metric", "entity", "intent", "concept"]
MetricOperation = Literal["sum", "avg", "count", "count_distinct", "growth"]
SemanticParameterType = Literal["limit", "period", "order", "comparison"]
SemanticTermSource = Literal["canonical", "synonym"]
SemanticParameterValue = str | int | float | bool


class SemanticTerm(BaseModel):
    term: str
    canonical: str
    type: SemanticTermType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: SemanticTermSource = "synonym"

    model_config = ConfigDict(frozen=True)


class SemanticParameter(BaseModel):
    type: SemanticParameterType
    value: SemanticParameterValue
    term: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    model_config = ConfigDict(frozen=True)


class SemanticMetric(BaseModel):
    name: str
    operation: MetricOperation
    column: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    equivalent_to: str | None = None
    expands_to: list[str] = Field(default_factory=list)
    ambiguity_policy: str | None = None

    model_config = ConfigDict(frozen=True)


class SemanticEntity(BaseModel):
    name: str
    column: str | None = None
    key: str | None = None
    date_fields: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class SemanticMappedColumn(BaseModel):
    term: str
    canonical: str
    column: str | list[str]
    role: Literal["metric", "dimension", "filter", "date"] = "dimension"

    model_config = ConfigDict(frozen=True)


class SemanticInterpretation(BaseModel):
    intent: str | None = None
    entity: str | None = None
    operation: str | None = None
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    filters: list[dict[str, Any]] = Field(default_factory=list)
    response_rule_ids: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class SemanticResolution(BaseModel):
    original_query: str
    normalized_query: str
    matched_terms: list[SemanticTerm] = Field(default_factory=list)
    parameters: list[SemanticParameter] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    suggested_metrics: list[SemanticMetric] = Field(default_factory=list)
    suggested_entities: list[SemanticEntity] = Field(default_factory=list)
    mapped_columns: list[SemanticMappedColumn] = Field(default_factory=list)
    interpretation: SemanticInterpretation | None = None

    model_config = ConfigDict(frozen=True)


class SemanticResolutionRequest(BaseModel):
    question: str = Field(min_length=1)

    model_config = ConfigDict(frozen=True)


class SemanticResolutionResponse(BaseModel):
    resolution: SemanticResolution

    model_config = ConfigDict(frozen=True)

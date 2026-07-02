from typing import Literal

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
    synonyms: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class SemanticEntity(BaseModel):
    name: str
    synonyms: list[str] = Field(default_factory=list)

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

    model_config = ConfigDict(frozen=True)


class SemanticResolutionRequest(BaseModel):
    question: str = Field(min_length=1)

    model_config = ConfigDict(frozen=True)


class SemanticResolutionResponse(BaseModel):
    resolution: SemanticResolution

    model_config = ConfigDict(frozen=True)

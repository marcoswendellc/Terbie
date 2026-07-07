from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MetricOperation = Literal["sum", "avg", "count", "count_distinct", "growth"]


class KBMetric(BaseModel):
    name: str
    operation: MetricOperation | None = None
    column: str | None = None
    formula: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    priority: int = 100
    contexts: list[str] = Field(default_factory=list)
    equivalent_to: str | None = None
    expands_to: list[str] = Field(default_factory=list)
    ambiguity_policy: Literal["prefer_default", "return_all"] | None = None

    model_config = ConfigDict(frozen=True)


class KBDimension(BaseModel):
    name: str
    column: str | None = None
    key: str | None = None
    derived_from: str | None = None
    derivation_rule: str | None = None
    date_fields: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    priority: int = 100
    contexts: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class KBIntent(BaseModel):
    name: str
    operation: str
    synonyms: list[str] = Field(default_factory=list)
    priority: int = 100
    response_rule_ids: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class KBBusinessRule(BaseModel):
    id: str
    description: str
    fields: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    condition: dict[str, object] = Field(default_factory=dict)
    effect: dict[str, object] = Field(default_factory=dict)
    priority: int = 100

    model_config = ConfigDict(frozen=True)


class KBResponseRule(BaseModel):
    id: str
    intent: str | None = None
    entity: str | None = None
    description: str
    must_include: list[str] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    priority: int = 100

    model_config = ConfigDict(frozen=True)


class KBCalculatedField(BaseModel):
    name: str
    formula: str
    dependencies: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class KBRelationship(BaseModel):
    id: str
    source_entity: str
    target_entity: str
    fields: list[str] = Field(default_factory=list)
    cardinality: str | None = None
    description: str | None = None

    model_config = ConfigDict(frozen=True)


class KBContextRule(BaseModel):
    id: str
    description: str
    triggers: list[str] = Field(default_factory=list)
    defaults: dict[str, object] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class KBPriorityRule(BaseModel):
    id: str
    description: str
    target: str
    priority: int

    model_config = ConfigDict(frozen=True)


class KBDisambiguationRule(BaseModel):
    id: str
    description: str
    terms: list[str] = Field(default_factory=list)
    prefer: str
    when: dict[str, object] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class KBExample(BaseModel):
    id: str
    question: str
    interpretation: dict[str, object]
    expected_response: str
    protected: bool = True

    model_config = ConfigDict(frozen=True)


class SemanticKnowledgeBase(BaseModel):
    version: str
    metrics: list[KBMetric] = Field(default_factory=list)
    dimensions: list[KBDimension] = Field(default_factory=list)
    intents: list[KBIntent] = Field(default_factory=list)
    business_rules: list[KBBusinessRule] = Field(default_factory=list)
    response_rules: list[KBResponseRule] = Field(default_factory=list)
    calculated_fields: list[KBCalculatedField] = Field(default_factory=list)
    relationships: list[KBRelationship] = Field(default_factory=list)
    contexts: list[KBContextRule] = Field(default_factory=list)
    priorities: list[KBPriorityRule] = Field(default_factory=list)
    disambiguation_rules: list[KBDisambiguationRule] = Field(default_factory=list)
    examples: list[KBExample] = Field(default_factory=list)
    column_mappings: dict[str, str | list[str]] = Field(default_factory=dict)
    metric_resolution: dict[str, object] = Field(default_factory=dict)
    response_best_practices: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)

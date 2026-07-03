from pydantic import BaseModel, ConfigDict, Field


class EntityCandidate(BaseModel):
    field: str
    value: str
    entity_type: str
    aliases: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class EntityMatch(BaseModel):
    field: str
    value: str
    entity_type: str
    confidence: float
    strategy: str

    model_config = ConfigDict(frozen=True)


class EntityResolutionResult(BaseModel):
    matches: list[EntityMatch] = Field(default_factory=list)
    is_ambiguous: bool = False
    ambiguity_message: str | None = None

    model_config = ConfigDict(frozen=True)

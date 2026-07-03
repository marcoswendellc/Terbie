from pydantic import BaseModel, ConfigDict, Field


class IntentGuardResult(BaseModel):
    is_analytical: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    response: str | None = None

    model_config = ConfigDict(frozen=True)

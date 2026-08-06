from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

IntentType = Literal[
    "greeting",
    "capability",
    "data_query",
    "clarification",
    "out_of_scope",
]


class IntentGuardResult(BaseModel):
    intent: IntentType
    requires_data: bool
    should_stop: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    response: str | None = None

    model_config = ConfigDict(frozen=True)

    @property
    def is_analytical(self) -> bool:
        """Backward-compatible view used by older callers."""
        return self.requires_data and not self.should_stop

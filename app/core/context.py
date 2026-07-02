from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

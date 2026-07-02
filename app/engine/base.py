from abc import ABC, abstractmethod
from typing import Any

from app.core.context import ExecutionContext


class BaseEngine(ABC):
    @abstractmethod
    def execute(
        self,
        plan: dict[str, Any],
        context: ExecutionContext,
    ) -> Any:
        """Execute a prepared plan within an execution context."""
        raise NotImplementedError

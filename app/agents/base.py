from abc import ABC, abstractmethod
from typing import Any

from app.core.context import ExecutionContext


class BaseAgent(ABC):
    @abstractmethod
    def run(
        self,
        input_data: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Run the agent contract for a given input and context."""
        raise NotImplementedError

from abc import ABC, abstractmethod
from typing import Any


class BaseMemory(ABC):
    @abstractmethod
    def save(self, key: str, value: dict[str, Any]) -> None:
        """Persist a value under a key."""
        raise NotImplementedError

    @abstractmethod
    def load(self, key: str) -> dict[str, Any] | None:
        """Load a value by key."""
        raise NotImplementedError

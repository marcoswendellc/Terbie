from datetime import UTC, datetime, timedelta
from threading import RLock

from app.memory.base import BaseMemory


class InMemorySessionStore(BaseMemory):
    """Process-local, TTL-bound storage. Entries are strictly keyed by session id."""

    def __init__(self, *, ttl_minutes: int = 60) -> None:
        self._values: dict[str, dict] = {}
        self._expires: dict[str, datetime] = {}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._lock = RLock()

    def save(self, key: str, value: dict) -> None:
        with self._lock:
            self._values[key] = value
            self._expires[key] = datetime.now(UTC) + self._ttl

    def load(self, key: str) -> dict | None:
        with self._lock:
            expiry = self._expires.get(key)
            if expiry is None or expiry <= datetime.now(UTC):
                self._values.pop(key, None)
                self._expires.pop(key, None)
                return None
            return self._values.get(key)

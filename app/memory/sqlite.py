import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock

from app.memory.base import BaseMemory


class SQLiteSessionStore(BaseMemory):
    """Persistent session storage suitable for a single-node deployment."""

    def __init__(self, path: str, *, ttl_minutes: int = 60) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._ttl = timedelta(minutes=ttl_minutes)
        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS sessions ("
                "session_id TEXT PRIMARY KEY, payload TEXT NOT NULL, expires_at TEXT NOT NULL)",
            )

    def save(self, key: str, value: dict) -> None:
        expires_at = (datetime.now(UTC) + self._ttl).isoformat()
        payload = json.dumps(value, ensure_ascii=False, default=str)
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO sessions(session_id, payload, expires_at) VALUES (?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET payload=excluded.payload, "
                "expires_at=excluded.expires_at",
                (key, payload, expires_at),
            )

    def load(self, key: str) -> dict | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload, expires_at FROM sessions WHERE session_id = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            if datetime.fromisoformat(row[1]) <= datetime.now(UTC):
                connection.execute("DELETE FROM sessions WHERE session_id = ?", (key,))
                return None
            return json.loads(row[0])

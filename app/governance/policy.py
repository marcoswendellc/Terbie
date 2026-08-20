import re
import unicodedata


class DataGovernancePolicy:
    """Applies output-level privacy and sensitive-column controls."""

    _SENSITIVE_PATTERNS = (
        r"(^|_)(senha|password|token|secret|credencial)($|_)",
        r"(^|_)(cpf|cnpj|email|telefone|celular)($|_)",
    )

    def __init__(self, *, minimum_group_size: int = 1) -> None:
        self._minimum_group_size = max(minimum_group_size, 1)

    def sanitize(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        sanitized: list[dict[str, object]] = []
        for row in rows:
            group_size = row.get("clientes_unicos")
            if (
                isinstance(group_size, int | float)
                and group_size < self._minimum_group_size
                and len(rows) > 1
            ):
                continue
            sanitized.append(
                {
                    key: value
                    for key, value in row.items()
                    if not self._is_sensitive(key)
                },
            )
        return sanitized

    def _is_sensitive(self, field: str) -> bool:
        normalized = "".join(
            char
            for char in unicodedata.normalize("NFKD", field.casefold())
            if not unicodedata.combining(char)
        )
        return any(re.search(pattern, normalized) for pattern in self._SENSITIVE_PATTERNS)

import re
import unicodedata


class DataGovernancePolicy:
    """Applies output-level privacy and sensitive-column controls."""

    _SENSITIVE_PATTERNS = (
        r"(^|_)(senha|password|token|secret|credencial)($|_)",
        r"(^|_)(cpf|cnpj|email|telefone|celular)($|_)",
    )

    def __init__(
        self,
        *,
        minimum_group_size: int = 1,
        allowed_shoppings: set[str] | None = None,
    ) -> None:
        self._minimum_group_size = max(minimum_group_size, 1)
        self._allowed_shoppings = {value.casefold() for value in (allowed_shoppings or set())}

    def sanitize(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        sanitized: list[dict[str, object]] = []
        for row in rows:
            shopping = row.get("nm_empreendimento") or row.get("shopping")
            if (
                self._allowed_shoppings
                and isinstance(shopping, str)
                and shopping.casefold() not in self._allowed_shoppings
            ):
                continue
            group_size = row.get("clientes_unicos")
            if (
                isinstance(group_size, int | float)
                and group_size < self._minimum_group_size
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

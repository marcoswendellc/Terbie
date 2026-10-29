import re
import unicodedata

import pandas as pd


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

    @property
    def minimum_group_size(self) -> int:
        return self._minimum_group_size

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

    def scope_source(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Restrict source rows before calculating aggregates."""
        if not self._allowed_shoppings:
            return dataframe
        column = next(
            (name for name in ("nm_empreendimento", "shopping") if name in dataframe),
            None,
        )
        if column is None:
            return dataframe.iloc[:0].copy()
        allowed = {value.strip() for value in self._allowed_shoppings}
        mask = dataframe[column].astype("string").str.strip().str.casefold().isin(allowed)
        return dataframe.loc[mask].copy()

    def _is_sensitive(self, field: str) -> bool:
        normalized = "".join(
            char
            for char in unicodedata.normalize("NFKD", field.casefold())
            if not unicodedata.combining(char)
        )
        return any(re.search(pattern, normalized) for pattern in self._SENSITIVE_PATTERNS)

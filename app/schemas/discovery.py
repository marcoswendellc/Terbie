from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.models.schema import ColumnDataType, ColumnSchema, ComparableValue, TableSchema

if TYPE_CHECKING:
    import pandas as pd


class SchemaDiscovery:
    """Discovers structural metadata from tabular data."""

    _EXAMPLE_LIMIT = 5

    def discover(self, table_name: str, data_frame: pd.DataFrame) -> TableSchema:
        columns = [
            self._discover_column(column_name=str(column_name), series=data_frame[column_name])
            for column_name in data_frame.columns
        ]

        return TableSchema(name=table_name, row_count=len(data_frame), columns=columns)

    def _discover_column(self, column_name: str, series: pd.Series[Any]) -> ColumnSchema:
        non_null_series = series.dropna()
        data_type = self._infer_type(non_null_series)
        min_value, max_value = self._calculate_range(non_null_series, data_type)

        return ColumnSchema(
            name=column_name,
            data_type=data_type,
            nullable=bool(series.isna().any()),
            null_count=int(series.isna().sum()),
            unique_count=int(non_null_series.nunique()),
            min_value=min_value,
            max_value=max_value,
            examples=self._examples(non_null_series),
        )

    def _infer_type(self, series: pd.Series[Any]) -> ColumnDataType:
        import pandas as pd
        from pandas.api import types as pandas_types

        if series.empty:
            return "string"

        if pandas_types.is_bool_dtype(series):
            return "boolean"

        if pandas_types.is_numeric_dtype(series):
            return "number"

        if pandas_types.is_datetime64_any_dtype(series):
            return "datetime"

        if self._can_parse_boolean(series):
            return "boolean"

        numeric_series = pd.to_numeric(series, errors="coerce")
        if numeric_series.notna().all():
            return "number"

        datetime_series = pd.to_datetime(series, errors="coerce", format="mixed", utc=True)
        if datetime_series.notna().all():
            return "datetime"

        return "string"

    def _calculate_range(
        self,
        series: pd.Series[Any],
        data_type: ColumnDataType,
    ) -> tuple[ComparableValue, ComparableValue]:
        import pandas as pd

        if series.empty or data_type not in {"number", "datetime"}:
            return None, None

        comparable_series = (
            pd.to_numeric(series, errors="coerce")
            if data_type == "number"
            else pd.to_datetime(series, errors="coerce", format="mixed", utc=True)
        ).dropna()

        if comparable_series.empty:
            return None, None

        return self._normalize_value(comparable_series.min()), self._normalize_value(
            comparable_series.max(),
        )

    def _examples(self, series: pd.Series[Any]) -> list[Any]:
        examples = series.drop_duplicates().head(self._EXAMPLE_LIMIT).tolist()
        return [self._normalize_value(value) for value in examples]

    def _can_parse_boolean(self, series: pd.Series[Any]) -> bool:
        allowed_values = {"true", "false", "yes", "no", "1", "0"}
        normalized = {str(value).strip().lower() for value in series.tolist()}
        return bool(normalized) and normalized.issubset(allowed_values)

    def _normalize_value(self, value: Any) -> Any:
        import pandas as pd

        if pd.isna(value):
            return None

        if hasattr(value, "item"):
            value = value.item()

        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()

        if isinstance(value, datetime):
            return value

        return value

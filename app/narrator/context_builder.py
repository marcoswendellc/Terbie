from typing import Any

from app.executor.models import ExecutionResult
from app.narrator.models import NarrativeContext, NarratorRequest


class NarrativeContextBuilder:
    """Builds a small safe context from an ExecutionResult."""

    def build(self, request: NarratorRequest) -> NarrativeContext:
        execution_result = ExecutionResult.model_validate(request.execution_result)
        data = execution_result.data
        columns = list(data[0].keys()) if data else []

        return NarrativeContext(
            question=request.question,
            rows_returned=execution_result.rows_returned,
            data=data,
            columns=columns,
            top_row=data[0] if data else None,
            metric_columns=self._metric_columns(data=data, columns=columns),
            dimension_columns=self._dimension_columns(data=data, columns=columns),
            warnings=execution_result.warnings,
            intent=getattr(request.execution_plan, "intent", None),
        )

    def _metric_columns(self, *, data: list[dict[str, Any]], columns: list[str]) -> list[str]:
        if not data:
            return []

        return [column for column in columns if isinstance(data[0].get(column), int | float)]

    def _dimension_columns(self, *, data: list[dict[str, Any]], columns: list[str]) -> list[str]:
        if not data:
            return []

        metric_columns = self._metric_columns(data=data, columns=columns)
        return [column for column in columns if column not in metric_columns]

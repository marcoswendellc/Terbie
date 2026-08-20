from typing import TYPE_CHECKING, Any

from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.executor.operations.filter import FilterOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class FilterGroupOperation(BaseOperation):
    """Evaluates a nested AND/OR filter expression over the original rows."""

    operation_type = "filter_group"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        expression = operation.parameters.get("expression")
        if not isinstance(expression, dict):
            context.warnings.append("Expressão de filtro composto inválida.")
            return dataframe

        return dataframe[self._mask(dataframe, expression, context)]

    def _mask(
        self,
        dataframe: "pd.DataFrame",
        expression: dict[str, Any],
        context: ExecutionContext,
    ) -> "pd.Series":
        import pandas as pd

        clauses = expression.get("clauses", [])
        if isinstance(clauses, list) and clauses:
            masks = [
                self._mask(dataframe, clause, context)
                for clause in clauses
                if isinstance(clause, dict)
            ]
            if not masks:
                return pd.Series(True, index=dataframe.index)
            result = masks[0]
            for mask in masks[1:]:
                result = result | mask if expression.get("logical") == "or" else result & mask
            return result

        field = expression.get("field")
        if not isinstance(field, str):
            return pd.Series(True, index=dataframe.index)
        filtered = FilterOperation().execute(
            dataframe,
            PlanOperation(
                type="filter",
                field=field,
                parameters={
                    "operator": expression.get("operator", "equals"),
                    "value": expression.get("value"),
                },
            ),
            context,
        )
        return pd.Series(dataframe.index.isin(filtered.index), index=dataframe.index)

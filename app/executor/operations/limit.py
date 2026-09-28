from typing import TYPE_CHECKING

from app.core.exceptions import AnalyticalExecutionError
from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class LimitOperation(BaseOperation):
    operation_type = "limit"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        value = operation.parameters.get("value")
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise AnalyticalExecutionError("Limite de linhas inválido.")

        context.metadata["executed_limit"] = value
        context.metadata["rows_available_before_limit"] = len(dataframe)
        tie_field = operation.parameters.get("keep_ties")
        if isinstance(tie_field, str) and tie_field in dataframe and len(dataframe) > value:
            boundary = dataframe.iloc[value - 1][tie_field]
            first = dataframe.head(value)
            ties = dataframe.iloc[value:]
            ties = ties[ties[tie_field] == boundary]
            import pandas as pd

            return pd.concat([first, ties])
        return dataframe.head(value)

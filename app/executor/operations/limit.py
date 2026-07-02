from typing import TYPE_CHECKING

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
        _ = context
        value = operation.parameters.get("value")
        if not isinstance(value, int) or value <= 0:
            return dataframe

        return dataframe.head(value)

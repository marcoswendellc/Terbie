from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class DistinctOperation(BaseOperation):
    operation_type = "distinct"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        subset = operation.parameters.get("subset")
        if subset is not None and not isinstance(subset, list):
            context.warnings.append("Distinct com subset inválido.")
            return dataframe.drop_duplicates()

        fields = [field for field in (subset or []) if field in dataframe.columns]
        if fields:
            return dataframe.drop_duplicates(subset=fields)

        return dataframe.drop_duplicates()

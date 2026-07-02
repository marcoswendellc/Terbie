from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class SortOperation(BaseOperation):
    operation_type = "sort"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        field = operation.field
        if field is None or field not in dataframe.columns:
            context.warnings.append(f"Campo de ordenação não encontrado: {field}.")
            return dataframe

        direction = operation.parameters.get("direction", "desc")
        return dataframe.sort_values(by=field, ascending=direction == "asc")

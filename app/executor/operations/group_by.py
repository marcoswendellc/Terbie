from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class GroupByOperation(BaseOperation):
    operation_type = "group_by"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        column = context.resolve_dimension_column(operation.field)
        if column is None:
            context.warnings.append("Operação group_by sem campo definido.")
            return dataframe

        if column not in dataframe.columns:
            context.warnings.append(f"Campo de agrupamento não encontrado: {column}.")
            return dataframe

        context.group_by_fields = [column]
        context.metadata["group_by_fields"] = context.group_by_fields
        return dataframe

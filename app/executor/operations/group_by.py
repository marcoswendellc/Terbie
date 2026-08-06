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
        requested_fields = operation.parameters.get("fields")
        fields = requested_fields if isinstance(requested_fields, list) else [operation.field]
        columns = [context.resolve_dimension_column(field) for field in fields]
        columns = [column for column in columns if column is not None]
        if not columns:
            context.warnings.append("Operação group_by sem campo definido.")
            return dataframe

        missing_columns = [column for column in columns if column not in dataframe.columns]
        if missing_columns:
            context.warnings.append(
                f"Campo de agrupamento não encontrado: {', '.join(missing_columns)}."
            )
            return dataframe

        context.group_by_fields = columns
        context.metadata["group_by_fields"] = context.group_by_fields
        return dataframe

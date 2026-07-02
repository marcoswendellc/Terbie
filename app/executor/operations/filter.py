from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class FilterOperation(BaseOperation):
    operation_type = "filter"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        field = context.resolve_dimension_column(operation.field)
        value = operation.parameters.get("value")
        if field is None or value is None:
            context.warnings.append("Filtro sem campo ou valor definido.")
            return dataframe

        if field not in dataframe.columns:
            context.warnings.append(f"Campo de filtro não encontrado: {field}.")
            return dataframe

        return dataframe[dataframe[field] == value]

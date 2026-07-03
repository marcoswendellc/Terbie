from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class SelectOperation(BaseOperation):
    operation_type = "select"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        fields = operation.parameters.get("fields", [])
        if not isinstance(fields, list):
            context.warnings.append("Seleção sem lista de campos.")
            return dataframe

        selected_fields = [field for field in fields if field in dataframe.columns]
        missing_fields = sorted(set(fields) - set(selected_fields))
        if missing_fields:
            context.warnings.append(f"Campos de seleção não encontrados: {missing_fields}.")

        if not selected_fields:
            return dataframe

        return dataframe[selected_fields]

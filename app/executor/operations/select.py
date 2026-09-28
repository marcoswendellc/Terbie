from typing import TYPE_CHECKING

from app.core.exceptions import AnalyticalExecutionError
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
        if not isinstance(fields, list) or not fields:
            raise AnalyticalExecutionError("Seleção sem lista de campos.")

        selected_fields = [field for field in fields if field in dataframe.columns]
        missing_fields = sorted(set(fields) - set(selected_fields))
        if missing_fields:
            raise AnalyticalExecutionError("Campos de seleção não encontrados.")

        if not selected_fields:
            raise AnalyticalExecutionError("Seleção sem campos disponíveis.")

        return dataframe[selected_fields]

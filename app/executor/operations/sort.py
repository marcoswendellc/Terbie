from typing import TYPE_CHECKING

from app.core.exceptions import AnalyticalExecutionError
from app.executor.context import ExecutionContext
from app.executor.dates import date_series
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
            raise AnalyticalExecutionError("Campo de ordenação não encontrado.")

        direction = operation.parameters.get("direction", "desc")
        if direction not in {"asc", "desc"}:
            raise AnalyticalExecutionError("Direção de ordenação inválida.")
        if operation.parameters.get("data_type") == "date":
            import pandas as pd

            dataframe = dataframe.copy()
            for date_field in operation.parameters.get("date_fields", [field]):
                dataframe[date_field] = date_series(dataframe[date_field]).dt.strftime("%Y-%m-%d")
            valid = dataframe[field].notna()
            cutoff = operation.parameters.get("as_of")
            if cutoff:
                valid &= dataframe[field].le(pd.Timestamp(cutoff).strftime("%Y-%m-%d"))
            if operation.parameters.get("year"):
                valid &= dataframe[field].str.startswith(
                    str(operation.parameters["year"]), na=False
                )
            if operation.parameters.get("active"):
                valid &= dataframe["sk_dtinicio"].le(cutoff) & dataframe["sk_dtfim"].ge(cutoff)
            dataframe = dataframe.loc[valid].where(dataframe.notna(), None)
            context.metadata["temporal_selection"] = {
                "field": field,
                "direction": direction,
                "as_of": cutoff,
            }
        context.metadata["order"] = direction
        context.metadata["order_by"] = field
        return dataframe.sort_values(by=field, ascending=direction == "asc", kind="stable")

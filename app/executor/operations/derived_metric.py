import pandas as pd

from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation


class DerivedMetricOperation(BaseOperation):
    operation_type = "derived_metric"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        numerator = operation.parameters.get("numerator")
        denominator = operation.parameters.get("denominator")
        alias = operation.alias
        if not isinstance(numerator, str) or not isinstance(denominator, str) or alias is None:
            context.warnings.append("Métrica derivada sem parâmetros suficientes.")
            return dataframe

        if numerator not in dataframe.columns or denominator not in dataframe.columns:
            context.warnings.append("Campos da métrica derivada não encontrados.")
            return dataframe

        numerator_values = pd.to_numeric(dataframe[numerator], errors="coerce")
        denominator_values = pd.to_numeric(dataframe[denominator], errors="coerce")
        result = dataframe.copy()
        result[alias] = numerator_values.div(denominator_values).fillna(0)
        return result

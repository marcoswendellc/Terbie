from app.core.exceptions import AnalyticalExecutionError
from app.executor.dates import date_series
from app.executor.operations.base import BaseOperation


class DeriveMonthOperation(BaseOperation):
    operation_type = "derive_month"

    def execute(self, dataframe, operation, context):
        field = operation.field
        if field not in dataframe.columns:
            raise AnalyticalExecutionError("Data da compra não encontrada para evolução mensal.")
        dates = date_series(dataframe[field])
        valid = dates.notna()
        year = operation.parameters.get("year")
        if year is not None:
            valid &= dates.dt.year.eq(int(year))
        start = operation.parameters.get("start_month", 1)
        end = operation.parameters.get("end_month", 12)
        if start > end:
            raise AnalyticalExecutionError(
                "Intervalo mensal atravessa anos; informe os anos de início e fim."
            )
        valid &= dates.dt.month.between(start, end)
        result = dataframe.loc[valid].copy()
        result["mes"] = dates.loc[valid].dt.strftime("%Y-%m")
        context.metadata["monthly_scope"] = {"field": field, "year": year}
        if dates.isna().any():
            context.warnings.append(
                "Registros sem data de compra válida foram excluídos da evolução."
            )
        return result

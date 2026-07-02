from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class AggregateOperation(BaseOperation):
    operation_type = "aggregate"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        import pandas as pd

        alias = operation.alias or operation.field or "value"
        formula = context.metric_formula(alias)
        metric_column = operation.field or context.resolve_metric_column(alias)

        if formula == "faturamento / quantidade_compras":
            return self._ticket_medio(dataframe=dataframe, alias=alias, context=context)

        if operation.function != "sum":
            context.warnings.append(f"Agregação não suportada: {operation.function}.")
            return dataframe

        if metric_column is None or metric_column not in dataframe.columns:
            context.warnings.append(f"Campo de métrica não encontrado: {metric_column}.")
            return dataframe

        numeric_series = pd.to_numeric(dataframe[metric_column], errors="coerce")
        working_frame = dataframe.assign(**{metric_column: numeric_series})

        if context.group_by_fields:
            return (
                working_frame.groupby(context.group_by_fields, dropna=False)[metric_column]
                .sum()
                .reset_index(name=alias)
            )

        return pd.DataFrame([{alias: numeric_series.sum()}])

    def _ticket_medio(
        self,
        *,
        dataframe: "pd.DataFrame",
        alias: str,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        import pandas as pd

        value_column = context.resolve_metric_column("faturamento")
        purchase_column = context.resolve_metric_column("quantidade_compras")
        if (
            value_column is None
            or purchase_column is None
            or value_column not in dataframe.columns
            or purchase_column not in dataframe.columns
        ):
            context.warnings.append("Campos necessários para ticket_medio não encontrados.")
            return dataframe

        working_frame = dataframe.assign(
            **{value_column: pd.to_numeric(dataframe[value_column], errors="coerce")},
        )

        if context.group_by_fields:
            grouped = working_frame.groupby(context.group_by_fields, dropna=False)
            result = grouped.agg(
                faturamento=(value_column, "sum"),
                quantidade_compras=(purchase_column, "nunique"),
            ).reset_index()
            result[alias] = result["faturamento"] / result["quantidade_compras"]
            return result[[*context.group_by_fields, alias]]

        quantity = working_frame[purchase_column].nunique()
        value = working_frame[value_column].sum() / quantity if quantity else 0
        return pd.DataFrame([{alias: value}])

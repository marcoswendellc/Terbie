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

        metrics = operation.parameters.get("metrics")
        if isinstance(metrics, list):
            return self._multi_metric_aggregate(
                dataframe=dataframe,
                metrics=metrics,
                context=context,
            )

        alias = operation.alias or operation.field or "value"
        formula = context.metric_formula(alias)
        metric_column = operation.field or context.resolve_metric_column(alias)

        if formula == "faturamento / quantidade_compras":
            return self._ticket_medio(dataframe=dataframe, alias=alias, context=context)

        if operation.function not in {"sum", "count_distinct"}:
            context.warnings.append(f"Agregação não suportada: {operation.function}.")
            return dataframe

        if metric_column is None or metric_column not in dataframe.columns:
            context.warnings.append(f"Campo de métrica não encontrado: {metric_column}.")
            return dataframe

        if operation.function == "count_distinct":
            if context.group_by_fields:
                return (
                    dataframe.groupby(context.group_by_fields, dropna=False)[metric_column]
                    .nunique()
                    .reset_index(name=alias)
                )

            return pd.DataFrame([{alias: dataframe[metric_column].nunique()}])

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

    def _multi_metric_aggregate(
        self,
        *,
        dataframe: "pd.DataFrame",
        metrics: list[object],
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        import pandas as pd

        aggregations: dict[str, tuple[str, str]] = {}
        numeric_columns: dict[str, pd.Series] = {}
        for metric in metrics:
            if not isinstance(metric, dict):
                continue

            field = metric.get("field")
            function = metric.get("function")
            alias = metric.get("alias")
            if not isinstance(field, str) or not isinstance(alias, str):
                continue

            if field not in dataframe.columns:
                context.warnings.append(f"Campo de métrica não encontrado: {field}.")
                continue

            if function == "sum":
                numeric_columns[field] = pd.to_numeric(dataframe[field], errors="coerce")
                aggregations[alias] = (field, "sum")
            elif function == "count_distinct":
                aggregations[alias] = (field, "nunique")
            else:
                context.warnings.append(f"Agregação não suportada: {function}.")

        if not aggregations:
            return dataframe

        working_frame = dataframe.assign(**numeric_columns) if numeric_columns else dataframe
        if context.group_by_fields:
            return working_frame.groupby(context.group_by_fields, dropna=False).agg(
                **aggregations,
            ).reset_index()

        return pd.DataFrame(
            [
                {
                    alias: (
                        working_frame[field].sum()
                        if function == "sum"
                        else working_frame[field].nunique()
                    )
                    for alias, (field, function) in aggregations.items()
                },
            ],
        )

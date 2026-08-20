from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.numeric import numeric_series
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class StatisticsOperation(BaseOperation):
    """Generic deterministic statistical tools for analytical plans."""

    operation_type = "statistics"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        import pandas as pd

        function = operation.function or str(operation.parameters.get("function", "describe"))
        field = operation.field
        if not isinstance(field, str) or field not in dataframe.columns:
            context.warnings.append(f"Campo estatístico não encontrado: {field}.")
            return pd.DataFrame()

        values = numeric_series(dataframe[field]).dropna()
        if values.empty:
            return pd.DataFrame()

        if function == "describe":
            return pd.DataFrame(
                [
                    {
                        "campo": field,
                        "quantidade": int(values.count()),
                        "media": float(values.mean()),
                        "mediana": float(values.median()),
                        "desvio_padrao": float(values.std(ddof=0)),
                        "minimo": float(values.min()),
                        "p25": float(values.quantile(0.25)),
                        "p75": float(values.quantile(0.75)),
                        "maximo": float(values.max()),
                    },
                ],
            )

        if function == "share":
            dimension = operation.parameters.get("dimension")
            if not isinstance(dimension, str) or dimension not in dataframe.columns:
                context.warnings.append("Dimensão ausente para cálculo de participação.")
                return pd.DataFrame()
            grouped = dataframe.assign(__value=values.reindex(dataframe.index).fillna(0)).groupby(
                dimension,
                dropna=False,
            )["__value"].sum()
            total = float(grouped.sum())
            result = grouped.reset_index(name="valor")
            result["participacao"] = result["valor"] / total if total else 0.0
            return result

        if function == "outlier_iqr":
            q1, q3 = values.quantile([0.25, 0.75])
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            return dataframe[(numeric_series(dataframe[field]) < lower) | (numeric_series(dataframe[field]) > upper)]

        if function == "correlation":
            other_field = operation.parameters.get("other_field")
            if not isinstance(other_field, str) or other_field not in dataframe.columns:
                context.warnings.append("Segundo campo ausente para cálculo de correlação.")
                return pd.DataFrame()
            paired = pd.DataFrame(
                {
                    field: numeric_series(dataframe[field]),
                    other_field: numeric_series(dataframe[other_field]),
                },
            ).dropna()
            correlation = paired[field].corr(paired[other_field]) if len(paired) > 1 else 0.0
            return pd.DataFrame(
                [{"campo_x": field, "campo_y": other_field, "correlacao": correlation}],
            )

        if function == "trend":
            date_field = operation.parameters.get("date_field")
            frequency = str(operation.parameters.get("frequency", "MS"))
            if not isinstance(date_field, str) or date_field not in dataframe.columns:
                context.warnings.append("Campo de data ausente para análise de tendência.")
                return pd.DataFrame()
            dates = pd.to_datetime(dataframe[date_field], errors="coerce", format="mixed")
            working = pd.DataFrame({"data": dates, "valor": numeric_series(dataframe[field])})
            working = working.dropna()
            return (
                working.set_index("data")["valor"]
                .resample(frequency)
                .sum()
                .reset_index(name="valor")
            )

        context.warnings.append(f"Função estatística não suportada: {function}.")
        return pd.DataFrame()

from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class DeriveDemographicsOperation(BaseOperation):
    operation_type = "derive_demographics"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        import pandas as pd

        result = dataframe.copy()
        if "cd_sexo" in result.columns:
            normalized = result["cd_sexo"].astype("string").str.strip().str.upper()
            result["genero"] = normalized.map(
                {
                    "F": "Feminino",
                    "0": "Feminino",
                    "M": "Masculino",
                    "1": "Masculino",
                    "O": "Outros",
                },
            ).fillna("Não informado")
        else:
            context.warnings.append("Campo demográfico não encontrado: cd_sexo.")

        if "dt_nascimento" in result.columns:
            birth_dates = pd.to_datetime(result["dt_nascimento"], errors="coerce", dayfirst=True)
            today = pd.Timestamp.now().normalize()
            ages = today.year - birth_dates.dt.year
            before_birthday = (birth_dates.dt.month > today.month) | (
                (birth_dates.dt.month == today.month) & (birth_dates.dt.day > today.day)
            )
            ages = (ages - before_birthday.fillna(False).astype(int)).where(
                birth_dates.notna() & birth_dates.le(today),
            )
            result["idade"] = ages.astype("Int64")
            result["faixa_etaria"] = pd.cut(
                ages,
                bins=[-1, 17, 24, 34, 44, 59, float("inf")],
                labels=["0-17", "18-24", "25-34", "35-44", "45-59", "60+"],
            ).astype("string").fillna("Não informado")
        else:
            context.warnings.append("Campo demográfico não encontrado: dt_nascimento.")

        return result

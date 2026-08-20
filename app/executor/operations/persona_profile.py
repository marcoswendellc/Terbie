from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class PersonaProfileOperation(BaseOperation):
    operation_type = "persona_profile"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        import pandas as pd

        if "sk_cliente" not in dataframe.columns:
            context.warnings.append("Campo de cliente não encontrado para calcular a persona.")
            return pd.DataFrame()

        visitors = dataframe.dropna(subset=["sk_cliente"]).drop_duplicates("sk_cliente")
        if visitors.empty:
            return pd.DataFrame()

        gender, gender_share = self._dominant(visitors.get("genero"))
        age_band, age_share = self._dominant(visitors.get("faixa_etaria"))
        locality, locality_share = self._dominant(visitors.get("cidade"))
        context.metadata["persona_visitors"] = len(visitors)

        return pd.DataFrame(
            [
                {
                    "genero_predominante": gender,
                    "percentual_genero": gender_share,
                    "faixa_etaria_predominante": age_band,
                    "percentual_faixa_etaria": age_share,
                    "localidade_predominante": locality,
                    "percentual_localidade": locality_share,
                    "clientes_unicos": len(visitors),
                },
            ],
        )

    def _dominant(self, series: "pd.Series | None") -> tuple[str, float]:
        if series is None:
            return "Não informado", 0.0

        valid = series.astype("string").str.strip()
        valid = valid[valid.notna() & valid.ne("") & valid.ne("Não informado")]
        if valid.empty:
            return "Não informado", 0.0

        counts = valid.value_counts()
        return str(counts.index[0]), round(float(counts.iloc[0] / counts.sum()), 4)

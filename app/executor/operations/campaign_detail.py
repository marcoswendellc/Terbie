import logging
from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


logger = logging.getLogger(__name__)


class CampaignDetailOperation(BaseOperation):
    operation_type = "campaign_detail"
    _FIELD_LABELS = {
        "vl_compra": "faturamento total",
        "cd_compra": "quantidade de compras",
        "sk_cliente": "clientes únicos",
        "nm_segmento": "segmento",
        "nm_fantasa": "loja",
        "bairro": "bairro",
        "cidade": "cidade",
        "nm_empreendimento": "empreendimento",
        "sk_dtinicio": "período inicial",
        "sk_dtfim": "período final",
    }

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        import pandas as pd

        _ = operation
        if dataframe.empty:
            return pd.DataFrame([])

        missing_fields = [
            field for field in self._FIELD_LABELS if field not in dataframe.columns
        ]
        if missing_fields:
            logger.info(
                "Campaign detail optional fields are unavailable. missing_fields=%s",
                missing_fields,
            )
            context.warnings.append(
                "Alguns campos não estavam disponíveis para o detalhe da campanha: "
                + ", ".join(self._FIELD_LABELS[field] for field in missing_fields)
                + ".",
            )

        revenue = self._numeric_series(dataframe, "vl_compra")
        total_revenue = float(revenue.sum()) if revenue is not None else None
        purchase_count = self._nunique_or_none(dataframe, "cd_compra")
        customer_count = self._nunique_or_none(dataframe, "sk_cliente")

        row = {
            "nm_promocao": self._first_value(dataframe, "nm_promocao"),
            "faturamento_total": total_revenue,
            "quantidade_compras": purchase_count,
            "clientes_unicos": customer_count,
            "ticket_medio_por_compra": (
                total_revenue / purchase_count
                if total_revenue is not None and purchase_count
                else None
            ),
            "ticket_medio_por_cliente": (
                total_revenue / customer_count
                if total_revenue is not None and customer_count
                else None
            ),
            "segmento_principal": self._top_value(
                dataframe,
                columns=["nm_segmento", "segmento"],
                revenue=revenue,
            ),
            "loja_maior_faturamento": self._top_value(
                dataframe,
                columns=["nm_fantasa"],
                revenue=revenue,
            ),
            "bairro_principal": self._top_value(
                dataframe,
                columns=["bairro"],
                revenue=revenue,
            ),
            "cidade_principal": self._top_value(
                dataframe,
                columns=["cidade"],
                revenue=revenue,
            ),
            "empreendimento": self._first_value(dataframe, "nm_empreendimento")
            or self._first_value(dataframe, "shopping"),
            "periodo_inicio": self._min_value(dataframe, "sk_dtinicio"),
            "periodo_fim": self._max_value(dataframe, "sk_dtfim"),
            "campos_indisponiveis": [
                self._FIELD_LABELS[field] for field in missing_fields
            ],
        }

        return pd.DataFrame([row])

    def _numeric_series(self, dataframe: "pd.DataFrame", column: str):
        if column not in dataframe.columns:
            return None

        import pandas as pd

        return pd.to_numeric(dataframe[column], errors="coerce")

    def _nunique_or_none(self, dataframe: "pd.DataFrame", column: str) -> int | None:
        if column not in dataframe.columns:
            return None

        return int(dataframe[column].nunique(dropna=True))

    def _first_value(self, dataframe: "pd.DataFrame", column: str) -> object | None:
        if column not in dataframe.columns:
            return None

        values = dataframe[column].dropna()
        if values.empty:
            return None

        return values.iloc[0]

    def _min_value(self, dataframe: "pd.DataFrame", column: str) -> object | None:
        if column not in dataframe.columns:
            return None

        values = dataframe[column].dropna()
        if values.empty:
            return None

        return values.min()

    def _max_value(self, dataframe: "pd.DataFrame", column: str) -> object | None:
        if column not in dataframe.columns:
            return None

        values = dataframe[column].dropna()
        if values.empty:
            return None

        return values.max()

    def _top_value(
        self,
        dataframe: "pd.DataFrame",
        *,
        columns: list[str],
        revenue,
    ) -> object | None:
        for column in columns:
            if column not in dataframe.columns:
                continue
            if revenue is None:
                continue

            working_frame = dataframe.assign(__revenue=revenue).dropna(subset=[column])
            if working_frame.empty:
                continue

            aggregations = {"__revenue": ("__revenue", "sum")}
            sort_fields = ["__revenue"]
            if "cd_compra" in working_frame.columns:
                aggregations["__compras"] = ("cd_compra", "nunique")
                sort_fields.append("__compras")

            grouped = (
                working_frame.groupby(column, dropna=True)
                .agg(**aggregations)
                .reset_index()
                .sort_values(sort_fields, ascending=False)
            )
            if not grouped.empty:
                return grouped.iloc[0][column]

        return None

from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.numeric import numeric_series
from app.executor.operations.base import BaseOperation
from app.executor.operations.filter import FilterOperation
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class CampaignContextComparisonOperation(BaseOperation):
    operation_type = "campaign_context_comparison"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        import pandas as pd

        requested_contexts = operation.parameters.get("contexts", [])
        if not isinstance(requested_contexts, list):
            return pd.DataFrame()

        rows: list[dict[str, object]] = []
        filter_operation = FilterOperation()
        for requested in requested_contexts:
            if not isinstance(requested, dict):
                continue
            promotion = requested.get("promotion")
            shopping = requested.get("shopping")
            if not isinstance(promotion, str) or not isinstance(shopping, str):
                continue

            selected = filter_operation.execute(
                dataframe,
                PlanOperation(
                    type="filter",
                    field="nm_empreendimento",
                    parameters={"operator": "entity_match", "value": shopping},
                ),
                context,
            )
            resolved_shopping = context.metadata.get("resolved_entities", {}).get(
                "nm_empreendimento",
                shopping,
            )
            selected = filter_operation.execute(
                selected,
                PlanOperation(
                    type="filter",
                    field="nm_promocao",
                    parameters={"operator": "entity_match", "value": promotion},
                ),
                context,
            )
            resolved_promotion = context.metadata.get("resolved_entities", {}).get(
                "nm_promocao",
                promotion,
            )
            if selected.empty:
                continue

            revenue = float(numeric_series(selected["vl_compra"]).sum())
            purchases = int(selected["cd_compra"].nunique())
            customers = int(selected["sk_cliente"].nunique())
            rows.append(
                {
                    "campanha_contexto": f"{resolved_promotion} — {resolved_shopping}",
                    "faturamento": revenue,
                    "quantidade_compras": purchases,
                    "clientes_unicos": customers,
                    "ticket_medio": revenue / purchases if purchases else 0.0,
                },
            )

        return pd.DataFrame(rows)

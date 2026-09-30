from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.dates import date_series
from app.executor.numeric import numeric_series
from app.executor.operations.base import BaseOperation
from app.executor.operations.filter import FilterOperation
from app.planner.models import PlanOperation
from app.semantic.temporal import normalize_temporal_text

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
            # A shared year must not make distinct events (Mães/Pais) fuzzy matches.
            ignored = {"a", "as", "campanha", "promocao", "de", "da", "do", "das", "dos", "e"}
            requested_tokens = set(normalize_temporal_text(promotion).split()) - ignored
            selected = selected[
                selected["nm_promocao"].map(
                    lambda value: requested_tokens.issubset(
                        set(normalize_temporal_text(str(value)).split())
                    )
                )
            ]
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
                requested_label = requested.get("label")
                label = (
                    requested_label
                    if isinstance(requested_label, str) and requested_label.strip()
                    else f"{promotion} — {shopping}"
                )
                rows.append(
                    {
                        "campanha_contexto": label,
                        "faturamento": None,
                        "quantidade_compras": None,
                        "clientes_unicos": None,
                        "ticket_medio": None,
                    },
                )
                context.warnings.append(f"Não foram encontrados dados para {label}.")
                continue

            revenue = float(numeric_series(selected["vl_compra"]).sum())
            purchases = int(selected["cd_compra"].nunique())
            customers = int(selected["sk_cliente"].nunique())
            start = date_series(selected["sk_dtinicio"]).min() if "sk_dtinicio" in selected else pd.NaT
            end = date_series(selected["sk_dtfim"]).max() if "sk_dtfim" in selected else pd.NaT
            rows.append(
                {
                    "campanha_contexto": f"{resolved_promotion} — {resolved_shopping}",
                    "faturamento": revenue,
                    "quantidade_compras": purchases,
                    "clientes_unicos": customers,
                    "ticket_medio": revenue / purchases if purchases else 0.0,
                    "inicio_campanha": start.date().isoformat() if pd.notna(start) else None,
                    "fim_campanha": end.date().isoformat() if pd.notna(end) else None,
                },
            )

        # Keep absent metrics as None, rather than NaN numeric values.
        result = pd.DataFrame(rows).astype(object)
        return result.where(pd.notna(result), None)

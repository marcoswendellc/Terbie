"""Dispatch supported business questions over validated unique receipts."""

import json
from pathlib import Path

import pandas as pd

from app.executor.operations import business_customers, business_segments, business_temporal
from app.executor.operations.base import BaseOperation
from app.executor.operations.business_common import note, prepare
from app.executor.operations.business_demographics import derive_age_groups

CUSTOMERS = {
    "frequency",
    "concentration",
    "age_metrics",
    "purchase_repeat",
    "age_segments",
    "geo_ranking",
    "geo_ticket",
    "outside_city",
    "neighborhood_frequency",
}
SEGMENTS = {
    "segment_share",
    "store_customers",
    "segment_recurrence",
    "segment_pairs",
    "campaign_ranking",
    "campaign_frequency",
}
TEMPORAL = {"weekday", "ticket_evolution", "campaign_phases", "campaign_retention"}


class BusinessAnalysisOperation(BaseOperation):
    operation_type = "business_analysis"

    def execute(self, dataframe, operation, context):
        mode = operation.parameters.get("mode")
        context.metadata["business_analysis"] = {
            "mode": mode,
            "notes": [],
            "scope": operation.parameters.get("scope", []),
        }
        required = []
        if mode not in {"weekday", "ticket_evolution", "segment_share"}:
            required.append("sk_cliente")
        if mode in {"age_metrics", "age_segments"} and "faixa_etaria" not in dataframe:
            required.append("dt_nascimento")
        if mode in {"age_segments", "segment_share", "segment_recurrence", "segment_pairs"}:
            required.append("nm_segmento")
        if mode == "store_customers":
            required.append("nm_fantasa")
        if mode == "neighborhood_frequency":
            required.append("bairro")
        if mode in {"weekday", "ticket_evolution", "campaign_phases"}:
            required.append("dt_registro_mos")
        if (
            mode
            in {
                "campaign_phases",
                "campaign_retention",
                "campaign_ranking",
                "campaign_frequency",
                "ticket_evolution",
            }
            and "nm_promocao" not in dataframe
        ):
            required.append("nm_promocao")
        missing = [field for field in required if field not in dataframe]
        if missing:
            detail = "Campos necessários indisponíveis: " + ", ".join(missing) + "."
            note(context, detail)
            return pd.DataFrame([{"status": "missing_fields", "detail": detail}])
        source = (
            derive_age_groups(dataframe, context)
            if mode in {"age_metrics", "age_segments"}
            else dataframe
        )
        data = prepare(source, context)
        if mode in {
            "ticket_evolution",
            "campaign_ranking",
            "campaign_frequency",
            "campaign_phases",
            "campaign_retention",
            "outside_city",
        } or operation.parameters.get("by_campaign"):
            if "nm_promocao" in data or "cd_promocao" in data:
                excluded = int((~data["__has_campaign"]).sum())
                data = data[data["__has_campaign"]].copy()
                if excluded:
                    note(context, f"Excluídas {excluded} compras sem campanha identificada.")
        if data.empty:
            return pd.DataFrame()
        options = dict(operation.parameters)
        path = Path(__file__).resolve().parents[2] / "knowledge" / "shopping_cities.json"
        if path.exists():
            options["shopping_cities"] = json.loads(path.read_text(encoding="utf-8"))
        handler = (
            business_customers
            if mode in CUSTOMERS
            else business_segments
            if mode in SEGMENTS
            else business_temporal
            if mode in TEMPORAL
            else None
        )
        if handler is None:
            return pd.DataFrame([{"status": "unsupported_analysis"}])
        result = handler.analyze(data, mode, context, options)
        # Avoid NaN/inf in JSON responses, retaining explicit undefined metrics.
        result = result.replace([float("inf"), float("-inf")], float("nan")).astype(object)
        return result.where(pd.notna(result), None)

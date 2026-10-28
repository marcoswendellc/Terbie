"""Shared definitions for purchase-based business analyses."""

import math

import pandas as pd

from app.executor.dates import date_series
from app.executor.numeric import numeric_series
from app.semantic.temporal import normalize_temporal_text

METRICS = [
    "faturamento",
    "quantidade_compras",
    "clientes_unicos",
    "ticket_medio_por_compra",
    "ticket_medio_por_cliente",
    "frequencia_media",
]


def note(context, text):
    notes = context.metadata.setdefault("business_analysis", {}).setdefault("notes", [])
    if text not in notes:
        notes.append(text)


def campaign_keys(data):
    keys = [
        field
        for field in ("cd_empreendimento", "nm_empreendimento", "cd_promocao", "nm_promocao")
        if field in data
    ]
    if "cd_promocao" not in keys:
        keys.extend(field for field in ("sk_dtinicio", "sk_dtfim") if field in data)
    return keys


def summarize(data, groups):
    groups = list(dict.fromkeys(groups))
    columns = [*groups, *METRICS]
    if data.empty:
        return (
            pd.DataFrame(columns=columns)
            if groups
            else pd.DataFrame([{field: 0 if field in METRICS[:3] else None for field in METRICS}])
        )
    known = data[data.sk_cliente.notna()]
    if groups:
        result = (
            data.groupby(groups, dropna=False, observed=True)
            .agg(
                faturamento=("vl_compra", "sum"),
                quantidade_compras=("__purchase", "nunique"),
                clientes_unicos=("sk_cliente", "nunique"),
            )
            .reset_index()
        )
        customer_values = (
            known.groupby(groups, dropna=False, observed=True)
            .agg(
                __known_revenue=("vl_compra", "sum"),
                __known_purchases=("__purchase", "nunique"),
            )
            .reset_index()
        )
        result = result.merge(customer_values, on=groups, how="left")
    else:
        result = pd.DataFrame(
            [
                {
                    "faturamento": data.vl_compra.sum(),
                    "quantidade_compras": data.__purchase.nunique(),
                    "clientes_unicos": known.sk_cliente.nunique(),
                    "__known_revenue": known.vl_compra.sum(),
                    "__known_purchases": known.__purchase.nunique(),
                }
            ]
        )
    denominator = result.clientes_unicos.replace(0, float("nan"))
    result["ticket_medio_por_compra"] = result.faturamento / result.quantidade_compras.replace(
        0, float("nan")
    )
    result["ticket_medio_por_cliente"] = result["__known_revenue"] / denominator
    result["frequencia_media"] = result["__known_purchases"] / denominator
    return result[columns]


def prepare(dataframe, context):
    data = dataframe.copy()
    for column in data.select_dtypes(include=["object", "string"]).columns:
        if column == "__purchase":
            continue
        data[column] = data[column].map(
            lambda value: (
                pd.NA
                if isinstance(value, str)
                and value.strip().casefold() in {"", "null", "none", "nan", "não informado"}
                else value.strip()
                if isinstance(value, str)
                else value
            )
        )
    if "cidade" not in data and "localidade" in data:
        data["cidade"] = data.localidade
    if "sk_cliente" not in data:
        data["sk_cliente"] = pd.NA
    for column in ("sk_cliente", "cd_compra", "cd_promocao", "cd_empreendimento", "sk_loja"):
        if column in data:
            data[column] = data[column].astype("string").str.replace(r"\.0$", "", regex=True)
    data["vl_compra"] = numeric_series(data.vl_compra)
    valid = data.vl_compra.map(lambda value: pd.notna(value) and math.isfinite(float(value)))
    valid &= data.cd_compra.notna()
    invalid = int((~valid).sum())
    if invalid:
        note(
            context, f"Foram excluídos {invalid} registros sem compra identificada ou valor válido."
        )
    data = data[valid].copy()
    data["__has_campaign"] = False
    for field in ("cd_promocao", "nm_promocao"):
        if field in data:
            data["__has_campaign"] |= data[field].notna()
    for field in ("dt_registro_mos", "sk_dtinicio", "sk_dtfim"):
        if field in data:
            data[field] = date_series(data[field])
    names = (
        data.nm_empreendimento.map(lambda x: normalize_temporal_text(str(x)))
        if "nm_empreendimento" in data
        else pd.Series("escopo", index=data.index)
    )
    ids = (
        data.cd_empreendimento
        if "cd_empreendimento" in data
        else pd.Series(pd.NA, index=data.index, dtype="string")
    )
    named_ids = pd.DataFrame({"name": names, "identity": ids}).dropna()
    identity_map = named_ids.groupby("name").identity.agg(
        lambda values: values.iloc[0] if values.nunique() == 1 else pd.NA
    )
    ids = ids.fillna(names.map(identity_map))
    if "cd_empreendimento" in data:
        data["cd_empreendimento"] = ids
    data["__shopping_key"] = ids.fillna("nome:" + names)
    if "nm_empreendimento" in data:
        labels = data.groupby("__shopping_key").nm_empreendimento.agg(
            lambda values: (
                sorted(values.dropna().astype(str).unique())[0]
                if values.notna().any()
                else "Não informado"
            )
        )
        data["nm_empreendimento"] = data.__shopping_key.map(labels)
    if "cd_promocao" in data and "nm_promocao" in data:
        fallback = data.nm_promocao.fillna("Não informado").map(normalize_temporal_text)
        for field in ("sk_dtinicio", "sk_dtfim"):
            if field in data:
                fallback = fallback + ":" + data[field].astype("string").fillna("sem_data")
        identities = pd.DataFrame(
            {"shop": data.__shopping_key, "name": fallback, "identity": data.cd_promocao}
        ).dropna()
        mapping = (
            identities.groupby(["shop", "name"])
            .identity.agg(lambda values: values.iloc[0] if values.nunique() == 1 else pd.NA)
            .to_dict()
        )
        known = [
            mapping.get((shop, name), pd.NA)
            for shop, name in zip(data.__shopping_key, fallback, strict=True)
        ]
        data["cd_promocao"] = data.cd_promocao.fillna(pd.Series(known, index=data.index))
        data["cd_promocao"] = data.cd_promocao.fillna("nome:" + fallback)
        labels = data.groupby(["__shopping_key", "cd_promocao"]).nm_promocao.agg(
            lambda values: (
                sorted(values.dropna().astype(str).unique())[0]
                if values.notna().any()
                else "Não informado"
            )
        )
        data["nm_promocao"] = [
            labels.loc[(shop, campaign)]
            for shop, campaign in zip(data.__shopping_key, data.cd_promocao, strict=True)
        ]
    data["__purchase"] = list(zip(data.__shopping_key, data.cd_compra, strict=True))
    checks = [
        column
        for column in (
            "vl_compra",
            "sk_cliente",
            "cd_promocao",
            "nm_promocao",
            "sk_loja",
            "nm_fantasa",
            "nm_segmento",
            "dt_registro_mos",
            "sk_dtinicio",
            "sk_dtfim",
        )
        if column in data
    ]
    conflicts = data.groupby("__purchase")[checks].nunique(dropna=False).gt(1).any(axis=1)
    conflicting_ids = set(conflicts[conflicts].index)
    if conflicting_ids:
        note(
            context,
            f"Excluídas {len(conflicting_ids)} compras com valores ou vínculos conflitantes.",
        )
        data = data[~data.__purchase.isin(conflicting_ids)]
    before = len(data)
    data = data.drop_duplicates("__purchase").copy()
    if before != len(data):
        note(context, f"Removidas {before - len(data)} repetições da mesma compra.")
    unknown = int(data.sk_cliente.isna().sum())
    if unknown:
        note(
            context,
            f"Há {unknown} compras sem cliente identificado. Frequência e gasto por "
            "cliente usam apenas compras de clientes identificados.",
        )
    return data

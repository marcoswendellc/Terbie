"""Aggregated customer analytics over canonical, unique purchase rows."""

import re
import unicodedata
from math import ceil

import pandas as pd

from app.executor.operations.business_common import campaign_keys, note, summarize


def analyze(data, mode, context, options) -> pd.DataFrame:
    """Return aggregate metrics without disclosing customer identifiers."""
    per_campaign = options.get("by_campaign", mode == "frequency")
    keys = campaign_keys(data) if per_campaign else []
    if mode == "outside_city":
        keys = [field for field in ("cd_empreendimento", "nm_empreendimento") if field in data]
    missing = int(data.loc[data["sk_cliente"].isna(), "__purchase"].nunique())
    if missing:
        note(
            context,
            f"{missing} compras sem cliente identificado; excluidas das metricas de clientes.",
        )
    identified = data[data["sk_cliente"].notna()]
    if mode == "frequency":
        return summarize(identified, keys)
    if mode == "concentration":
        rows = []
        for labels, frame in _groups(data, keys):
            spend = (
                frame.dropna(subset=["sk_cliente"])
                .groupby("sk_cliente")["vl_compra"]
                .sum()
                .sort_values(ascending=False)
            )
            size = ceil(len(spend) * 0.1)
            revenue = frame["vl_compra"].sum()
            rows.append(
                {
                    **labels,
                    "clientes": len(spend),
                    "clientes_top_10_pct": size,
                    "receita": revenue,
                    "receita_top_10_pct": spend.iloc[:size].sum(),
                    "participacao_receita_top_10_pct": 100 * spend.iloc[:size].sum() / revenue
                    if revenue > 0
                    else None,
                }
            )
        note(
            context,
            "Top 10% usa teto da quantidade de clientes; empates no limite mantem "
            "exatamente essa quantidade. Receita total inclui compras sem cliente identificado.",
        )
        return pd.DataFrame(rows)
    if mode == "purchase_repeat":
        rows = []
        for labels, frame in _groups(identified, keys):
            counts = frame.groupby("sk_cliente")["__purchase"].nunique()
            for label, count in [
                ("compra_unica", int((counts == 1).sum())),
                ("multiplas_compras", int((counts > 1).sum())),
            ]:
                rows.append(
                    {
                        **labels,
                        "perfil_compra": label,
                        "clientes": count,
                        "proporcao_clientes": count / len(counts) if len(counts) else None,
                    }
                )
        return pd.DataFrame(rows)
    if mode == "outside_city":
        return _outside_city(data, keys, context, options)
    if mode == "geo_ranking":
        levels = []
        for level in ("cidade", "bairro"):
            if level not in data:
                continue
            groups = list(
                dict.fromkeys(keys + [field for field in ("uf", "cidade", level) if field in data])
            )
            result = summarize(data, groups)
            result["nivel_geografico"] = level
            levels.append(result)
        if not levels:
            return pd.DataFrame([{"status": "missing_dimension", "modo": mode}])
        note(
            context,
            "Resultados separados por cidade e bairro; totais entre niveis nao sao aditivos. "
            "Clientes podem aparecer em varios grupos.",
        )
        return (
            pd.concat(levels, ignore_index=True)
            .sort_values(
                ["nivel_geografico", "clientes_unicos", "faturamento"],
                ascending=[True, False, False],
                kind="stable",
            )
            .reset_index(drop=True)
        )
    dimensions = {
        "age_metrics": ["faixa_etaria"],
        "age_segments": ["faixa_etaria", "nm_segmento" if "nm_segmento" in data else "segmento"],
        "geo_ranking": ["uf", "cidade", "bairro"],
        "geo_ticket": ["regiao"] if "regiao" in data else ["uf", "cidade"],
        "neighborhood_frequency": ["uf", "cidade", "bairro"],
    }
    if mode not in dimensions:
        raise ValueError(f"Modo de clientes desconhecido: {mode}")
    if mode == "geo_ticket" and "regiao" not in data and "cidade" not in data:
        return pd.DataFrame([{"status": "missing_dimension", "modo": mode}])
    groups = list(dict.fromkeys(keys + [field for field in dimensions[mode] if field in data]))
    if not any(field in data for field in dimensions[mode]):
        return pd.DataFrame([{"status": "missing_dimension", "modo": mode}])
    result = summarize(data, groups)
    if mode == "geo_ticket" and "regiao" not in data:
        note(context, "Regiao nao disponivel: ticket geografico apresentado por cidade.")
    if mode == "geo_ranking":
        result = result.sort_values(
            ["clientes_unicos", "faturamento"], ascending=False, kind="stable"
        ).reset_index(drop=True)
    if mode in ("age_metrics", "geo_ticket"):
        result = result.sort_values(
            "ticket_medio_por_compra", ascending=False, kind="stable"
        ).reset_index(drop=True)
    elif mode == "neighborhood_frequency":
        result = result.sort_values("frequencia_media", ascending=False, kind="stable").reset_index(
            drop=True
        )
    elif mode == "age_segments":
        result = result.sort_values(
            ["faixa_etaria", "quantidade_compras"], ascending=[True, False], kind="stable"
        ).reset_index(drop=True)
    if mode in ("geo_ranking", "geo_ticket", "neighborhood_frequency", "age_segments"):
        note(
            context,
            "Clientes podem aparecer em mais de um grupo; contagens de clientes "
            "dos grupos nao sao aditivas.",
        )
    return result


def _groups(data, keys):
    if not keys:
        yield {}, data
        return
    for values, frame in data.groupby(keys, dropna=False, sort=False):
        values = values if isinstance(values, tuple) else (values,)
        yield dict(zip(keys, values, strict=True)), frame


def _normalize(value):
    if pd.isna(value):
        return None
    value = "".join(
        c for c in unicodedata.normalize("NFKD", str(value)) if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", value)).strip().casefold() or None


def _outside_city(data, keys, context, options):
    rows = []
    for labels, frame in _groups(data, keys):
        target = options.get("cidade_shopping") or options.get("cidade_empreendimento")
        if not target:
            target = next(
                (
                    value
                    for key, value in options.get("shopping_cities", {}).items()
                    if _normalize(key) == _normalize(labels.get("nm_empreendimento"))
                ),
                None,
            )
        if not target:
            for field in ("cidade_shopping", "cidade_empreendimento"):
                if field in frame:
                    cities = frame[field].dropna().unique()
                    if len(cities) == 1:
                        target = cities[0]
                        break
        if not target:
            rows.append({**labels, "status": "missing_shopping_city"})
            continue
        target_uf = None
        if isinstance(target, dict):
            target_uf = target.get("uf")
            target = target.get("cidade")
        if not target:
            rows.append({**labels, "status": "missing_shopping_city"})
            continue
        clients = frame.dropna(subset=["sk_cliente"]).copy()
        clients["_city"] = clients["cidade"].map(_normalize) if "cidade" in clients else None
        expected = _normalize(target)
        if target_uf:
            states = (
                clients.uf.map(_normalize)
                if "uf" in clients
                else pd.Series(None, index=clients.index)
            )
            clients["_city"] = [
                (city, state) if city and state else None
                for city, state in zip(clients._city, states, strict=True)
            ]
            expected = (_normalize(target), _normalize(target_uf))
        residences = clients.groupby("sk_cliente")["_city"].agg(lambda values: set(values.dropna()))
        known = residences[residences.map(len) == 1]
        conflicting = int((residences.map(len) > 1).sum())
        total = clients["sk_cliente"].nunique()
        outside = sum(expected not in cities for cities in known)
        unknown = int((residences.map(len) == 0).sum())
        rows.append(
            {
                **labels,
                "status": "ok",
                "cidade_shopping": target,
                "uf_shopping": target_uf,
                "clientes": total,
                "clientes_cidade_conhecida": len(known),
                "clientes_cidade_conflitante": conflicting,
                "clientes_cidade_desconhecida": unknown,
                "clientes_fora_cidade": outside,
                "proporcao_fora_cidade_conhecida": outside / len(known) if len(known) else None,
                "proporcao_cidade_desconhecida": unknown / total if total else None,
            }
        )
    note(
        context,
        "Fora da cidade usa apenas clientes com exatamente uma cidade conhecida no denominador. "
        "Clientes com cidades conflitantes e clientes sem cidade sao informados separadamente "
        "e excluidos desse denominador. Quando o cadastro contém UF, município e UF "
        "são comparados juntos; registros sem UF também ficam fora do denominador conhecido.",
    )
    return pd.DataFrame(rows)

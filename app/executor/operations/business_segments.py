"""Aggregated segment, store, and campaign purchasing indicators."""

from collections import Counter
from itertools import combinations

import pandas as pd

from app.executor.operations.business_common import campaign_keys, note, summarize


def _rank(result, metric, groups, options):
    result = result.sort_values(
        [metric] + groups,
        ascending=[False] + [True] * len(groups),
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)
    limit = options.get("limit")
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit deve ser um inteiro positivo.")
        result = result.head(limit)
    return result


def _pairs(data, context, options):
    columns = ["segmento_a", "segmento_b", "clientes_em_comum", "suporte_pct"]
    memberships = data[["sk_cliente", "nm_segmento"]].dropna().drop_duplicates()
    segments = memberships.groupby("sk_cliente", sort=False).nm_segmento.agg(list)
    work = sum(len(values) * (len(values) - 1) // 2 for values in segments)
    bound = options.get("max_pair_expansions", 1_000_000)
    if isinstance(bound, bool) or not isinstance(bound, int) or bound < 0:
        raise ValueError("max_pair_expansions deve ser um inteiro não negativo.")
    if work > bound:
        reason = (
            f"Análise recusada: {work} pares de segmentos excedem o limite de {bound}; "
            "restrinja o período ou os filtros."
        )
        note(context, reason)
        return pd.DataFrame([{"status": "recusado", "motivo": reason}])
    counts = Counter()
    for values in segments:
        counts.update(combinations(sorted(values), 2))
    denominator = len(segments)
    result = pd.DataFrame(
        [
            {
                "segmento_a": a,
                "segmento_b": b,
                "clientes_em_comum": count,
                "suporte_pct": count / denominator * 100,
            }
            for (a, b), count in counts.items()
        ],
        columns=columns,
    )
    note(
        context,
        "Pares não ordenados contam cada cliente uma vez por par. O suporte usa "
        "todos os clientes identificados com segmento conhecido; os suportes podem se "
        "sobrepor. Coocorrência não indica causalidade.",
    )
    return _rank(result, "clientes_em_comum", ["segmento_a", "segmento_b"], options)


def analyze(data, mode, context, options):
    """Return aggregate indicators without exposing individual client identifiers."""
    if mode == "segment_pairs":
        return _pairs(data, context, options)
    if mode in ("segment_share", "segment_recurrence"):
        groups = ["nm_segmento"]
    elif mode == "store_customers":
        groups = [
            column
            for column in ("cd_empreendimento", "nm_empreendimento", "sk_loja", "nm_fantasa")
            if column in data.columns
        ]
        if "nm_fantasa" not in groups:
            raise ValueError("A análise de lojas requer nm_fantasa.")
    elif mode in ("campaign_ranking", "campaign_frequency"):
        groups = campaign_keys(data)
    else:
        raise ValueError(f"Modo de análise desconhecido: {mode}")
    result = summarize(data, groups)
    if mode == "campaign_ranking" and options.get("ranking_metric"):
        criterion = {
            "faturamento": "faturamento",
            "quantidade_compras": "quantidade de compras",
            "clientes_unicos": "clientes únicos",
            "ticket_medio_por_compra": "ticket por compra",
        }[options["ranking_metric"]]
        note(context, "Campanhas comparadas por faturamento, compras e clientes únicos; "
             "os líderes podem ser diferentes conforme o indicador. "
             "A tabela é ordenada por " + criterion + ".")
    if mode == "campaign_ranking" and options.get("campaign_shares"):
        shopping = [
            field for field in ("cd_empreendimento", "nm_empreendimento") if field in result
        ]
        for metric, column in (
            ("faturamento", "participacao_faturamento_pct"),
            ("quantidade_compras", "participacao_compras_pct"),
        ):
            denominator = (
                result.groupby(shopping, dropna=False)[metric].transform("sum")
                if shopping else pd.Series(result[metric].sum(), index=result.index)
            )
            result[column] = result[metric] / denominator.where(denominator.gt(0)) * 100
        note(context, "Representatividade = valor da campanha dividido pelo total das "
             "campanhas identificadas do mesmo shopping e período, em percentual. "
             "Compras sem campanha não entram nesse denominador. "
             "São mostradas as participações em faturamento e compras separadamente.")
    if mode == "segment_share":
        revenue = data.vl_compra.sum()
        purchases = data.__purchase.nunique()
        result["participacao_faturamento_pct"] = (
            result.faturamento / revenue * 100 if revenue > 0 else float("nan")
        )
        result["participacao_compras_pct"] = (
            result.quantidade_compras / purchases * 100 if purchases > 0 else float("nan")
        )
        if revenue <= 0:
            note(context, "Participação de faturamento indefinida: faturamento total não positivo.")
    if mode == "store_customers":
        note(
            context,
            "Clientes únicos observados em compras por loja; esta classificação "
            "não demonstra atração ou efeito causal da loja.",
        )
    if mode == "campaign_frequency":
        note(
            context,
            "Frequência e gasto são calculados por cliente identificado dentro "
            "de cada campanha e apresentados de forma agregada; um cliente pode "
            "participar de várias campanhas.",
        )
    metric = {
        "store_customers": "clientes_unicos",
        "segment_recurrence": "ticket_medio_por_compra",
        "campaign_frequency": "frequencia_media",
    }.get(mode, "faturamento")
    if mode == "campaign_ranking":
        metric = options.get("ranking_metric", metric)
    return _rank(result, metric, groups, options)

"""Relative purchasing rankings calculated over canonical receipts."""

import math

import pandas as pd

from app.executor.operations.business_common import note, summarize
from app.knowledge.scoring import PERCENTILE_FIELDS, normalized_weights
from app.semantic.temporal import normalize_temporal_text


def add_percentile_score(indicators, weights=None):
    weights = normalized_weights(weights)
    result = indicators.copy()
    eligible = pd.Series(True, index=result.index)
    for metric in PERCENTILE_FIELDS:
        result[metric] = pd.to_numeric(result[metric], errors="coerce")
        eligible &= result[metric].map(lambda value: pd.notna(value) and math.isfinite(value))
    eligible &= result.quantidade_compras.gt(0)
    result = result.loc[eligible].copy()
    population = len(result)
    for metric, field in PERCENTILE_FIELDS.items():
        result[field] = (
            100 * (result[metric].rank(method="average") - 1) / (population - 1)
            if population > 1 else float("nan")
        )
    result["score"] = sum(
        result[PERCENTILE_FIELDS[metric]] * weight for metric, weight in weights.items()
    ).round(12)
    return result


def analyze(data, mode, context, options):
    entity = options["ranking_entity"]
    metric = options.get("ranking_metric", "score")
    shopping = [field for field in ("cd_empreendimento", "nm_empreendimento") if field in data]
    dimensions = {
        "loja": [*shopping, *[field for field in ("sk_loja", "nm_fantasa") if field in data]],
        "bairro": [field for field in ("uf", "cidade", "bairro") if field in data],
        "cliente": ["sk_cliente"],
    }[entity]
    identity = {"loja": "nm_fantasa", "bairro": "bairro", "cliente": "sk_cliente"}[entity]
    unknown = int(data.loc[data[identity].isna(), "__purchase"].nunique())
    if unknown:
        note(context, f"Excluídas {unknown} compras sem identificação de {entity} do ranking.")
    source = data[data[identity].notna()].copy()
    if entity == "loja":
        source["__store_key"] = (
            source.sk_loja if "sk_loja" in source else pd.Series(pd.NA, index=source.index)
        ).fillna("nome:" + source.nm_fantasa.map(normalize_temporal_text))
        source["nm_fantasa"] = source.groupby(
            ["__shopping_key", "__store_key"], dropna=False,
        ).nm_fantasa.transform(lambda values: sorted(values.unique())[0])
        dimensions = [*shopping, "__store_key", "nm_fantasa"]
    result = summarize(source, dimensions)
    minimum = options.get("minimum_group_size", 1)
    if result.clientes_unicos.lt(minimum).any():
        note(context, "Grupos abaixo do mínimo configurado de clientes únicos "
             "não participam do ranking nem dos percentis.")
        result = result[result.clientes_unicos.ge(minimum)].copy()
    if entity == "cliente":
        # References are assigned before sorting and have meaning only in this cohort.
        result = result.sort_values("sk_cliente", kind="stable").reset_index(drop=True)
        result["cliente"] = [f"Cliente {index + 1:03d}" for index in range(len(result))]
        result = result.drop(columns="sk_cliente")
        dimensions = ["cliente"]
        note(context, "Clientes apresentados com referências anônimas "
             "válidas somente neste recorte. "
             "Engajamento refere-se às compras registradas, não a visitas ou outras interações.")
    if metric == "score":
        weights = normalized_weights(options.get("score_weights"))
        before = len(result)
        result = add_percentile_score(result, weights)
        excluded = before - len(result)
        if excluded:
            note(context, f"Excluídas {excluded} entidades sem os três indicadores "
                 "válidos do score.")
        context.metadata["business_analysis"]["score"] = {
            "population": len(result), "weights": weights,
            "percentile_method": "100 * (rank_average - 1) / (n - 1)",
        }
        equal_weights = len(set(weights.values())) == 1
        note(context, "Score de 0 a 100 calculado pela média ponderada dos percentis de "
             "faturamento, quantidade de compras únicas e ticket por compra, "
             + ("com pesos iguais." if equal_weights else "com os pesos configurados."))
        note(context, "Percentis calculados entre todas as entidades elegíveis do mesmo recorte "
             "antes de aplicar o limite. Empates recebem a posição média. "
             "O score não representa participação percentual nem probabilidade.")
        note(context, f"População comparada: {len(result)} entidades elegíveis. Pesos: "
             + "; ".join(
                 f"{label} {weights[key] * 100:.2f}%".replace(".", ",")
                 for key, label in (("faturamento", "faturamento"),
                                    ("quantidade_compras", "compras"),
                                    ("ticket_medio_por_compra", "ticket por compra"))
             ) + ".")
        if len(result) == 1:
            note(context, "Score indisponível: há apenas uma entidade elegível neste recorte; "
                 "não há comparação por percentis.")
    else:
        labels = {"faturamento": "faturamento", "quantidade_compras": "quantidade de compras",
                  "clientes_unicos": "clientes únicos", "frequencia_media": "compras por cliente",
                  "ticket_medio_por_compra": "ticket por compra",
                  "ticket_medio_por_cliente": "gasto por cliente"}
        note(context, "Critério explícito: " + labels[metric] + ". Score não aplicado.")
    context.metadata["business_analysis"].update({
        "ranking_entity": entity, "ranking_metric": metric,
    })
    result = result.sort_values(
        [metric, *dimensions], ascending=[False, *[True] * len(dimensions)],
        kind="stable", na_position="last",
    )
    limit = options.get("limit")
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit deve ser um inteiro positivo.")
        result = result.head(limit)
    return result.drop(columns=["sk_loja", "__store_key"], errors="ignore").reset_index(drop=True)

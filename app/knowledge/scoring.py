"""One definition for the relative purchasing score and its configurable weights."""

import math

SCORE_WEIGHTS = {
    "faturamento": 1.0,
    "quantidade_compras": 1.0,
    "ticket_medio_por_compra": 1.0,
}
PERCENTILE_FIELDS = {
    "faturamento": "percentil_faturamento",
    "quantidade_compras": "percentil_compras",
    "ticket_medio_por_compra": "percentil_ticket",
}


def normalized_weights(weights=None):
    weights = SCORE_WEIGHTS if weights is None else weights
    if not isinstance(weights, dict) or set(weights) != set(PERCENTILE_FIELDS):
        raise ValueError("Informe os pesos dos três indicadores do score.")
    if any(
        isinstance(value, bool) or not isinstance(value, int | float)
        or not math.isfinite(value) or value < 0
        for value in weights.values()
    ):
        raise ValueError("Pesos devem ser números finitos não negativos.")
    total = sum(weights.values())
    if not math.isfinite(total) or total <= 0:
        raise ValueError("A soma dos pesos deve ser positiva e finita.")
    return {metric: weights[metric] / total for metric in PERCENTILE_FIELDS}

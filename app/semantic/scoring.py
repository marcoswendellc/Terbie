"""Recognize open purchasing rankings and preserve explicit metric criteria."""

import re

from app.semantic.temporal import normalize_temporal_text


def entity_ranking_options(question):
    text = normalize_temporal_text(question)
    if not re.search(r"\b(?:score|scores|representativ\w*|engajad\w*|engajamento)\b", text):
        return None
    entity = re.search(
        r"\b(?:qual|quais|top\s+\d+|ranking|scores?)\s+"
        r"(?:(?:foi|foram|e|sao|o|a|os|as|de|do|da|dos|das)\s+)*"
        r"(lojas?|clientes?|bairros?)\b", text,
    ) or re.search(r"\b(lojas?|clientes?|bairros?)\b", text)
    if not entity:
        return None
    entity = entity.group(1).removesuffix("s")
    metric = "score"
    if not re.search(r"\bscores?\b", text):
        criteria = [
            ("ticket_medio_por_cliente", r"\b(?:gasto|ticket)\s+medio\s+por\s+cliente\b"),
            ("ticket_medio_por_compra", r"\bticket\b"),
            ("frequencia_media", r"\bfrequencia\b|\bcompras\s+por\s+cliente\b"),
            ("faturamento", r"\b(?:faturamento|receita|valor\s+(?:das?|de)\s+compras)\b"),
            ("clientes_unicos", r"\bclientes\s+unicos\b|"
                                r"\b(?:numero|quantidade|total)\s+de\s+clientes\b"),
            ("quantidade_compras", r"\b(?:quantidade|volume|numero)\s+de\s+(?:compras|notas)\b|"
                                   r"\b(?:por|em|mais)\s+(?:compras|notas)\b"),
        ]
        metric = next((name for name, pattern in criteria if re.search(pattern, text)), "score")
    return {"ranking_entity": entity, "ranking_metric": metric}


def ranking_scope_filters(question):
    text = normalize_temporal_text(question)
    filters = []
    for dimension, field in (("loja", "nm_fantasa"), ("bairro", "bairro")):
        match = re.search(
            r"\b(?:na|no|da|do)\s+" + dimension + r"\s+(.+?)"
            r"(?=\s+(?:na|no|da|do|em|durante|qual|quais)\b|[,?;!]|$)", text,
        )
        if match:
            filters.append({"type": "filter", "field": field,
                            "operator": "normalized_equals", "value": match.group(1).strip()})
    return filters

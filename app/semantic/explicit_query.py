"""Keep explicit analytical instructions intact across model planning stages."""

import re

from app.context_resolution.context_resolver import ContextResolver
from app.semantic.purchase_scope import is_customer_profile, ticket_geography
from app.semantic.temporal import normalize_temporal_text


def is_explicit_query(question: str) -> bool:
    normalized = normalize_temporal_text(question)
    if is_customer_profile(question) or ticket_geography(question):
        return True
    if re.search(r"\b(compare|comparar|comparacao)\b", normalized):
        return False
    metric = re.search(r"\b(faturamento|receita|compras|notas|clientes|ticket)\b", normalized)
    if not metric:
        return False
    return bool(
        re.search(r"\b(por mes|mensal|mensais|mes a mes)\b", normalized)
        or ContextResolver().explicit_grouping(question)
        or re.search(r"\bqual\s+bairro\b.*\b(maior|mais)\b", normalized)
        or re.search(r"\bqual\s+(?:(?:foi\s+)?a\s+)?campanha\b.*\b(maior|melhor)\b", normalized)
    )

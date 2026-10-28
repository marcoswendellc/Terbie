import re

from app.semantic.temporal import normalize_temporal_text


def is_gender_purchase_comparison(question: str) -> bool:
    text = normalize_temporal_text(question)
    return bool(
        re.search(r"\bhomens\b", text)
        and re.search(r"\bmulheres\b", text)
        and re.search(r"\b(compra|compras|comprar|ticket|gasto|faturamento)\b", text)
        and re.search(r"\b(diferencas?|compare|comparar|comparacao|comportamento)\b", text)
    )


def requested_campaign(question: str) -> str | None:
    match = re.search(
        r"\b(?:campanha|promocao)\s+(?:de\s+)?(.+?)"
        r"(?=\s+(?:no|na|do|da)\b|[?;!]|$)", normalize_temporal_text(question),
    )
    return match.group(1).strip(' ."') if match else None

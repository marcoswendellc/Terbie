"""Expand a shared campaign name into two explicit year-specific requests."""

import re

from app.semantic.temporal import normalize_temporal_text


def expand_campaign_year_comparison(question: str) -> str | None:
    text = normalize_temporal_text(question).strip(" .?!")
    match = re.search(
        r"\b(?:compare|comparar)\s+(?:as?\s+)?"
        r"(?:campanhas?|promocao|promocoes)\s+(?:de\s+)?"
        r"(?P<event>.+?)\s+(?:de\s+)?(?P<first>(?:19|20)\d{2})\s+"
        r"(?:x|vs\.?|versus|e|com)\s+(?:de\s+)?(?P<second>(?:19|20)\d{2})\s+"
        r"(?:do|da|no|na)\s+(?P<shopping>.+)$",
        text,
    )
    if match is None:
        return None
    event, first, second, shopping = (
        match.group(key) for key in ("event", "first", "second", "shopping")
    )
    return (
        f"Compare a campanha {event} {first} do {shopping} "
        f"com a campanha {event} {second} do {shopping}"
    )

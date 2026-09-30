import re
from calendar import monthrange

from app.semantic.temporal import normalize_temporal_text

MONTHS = (
    "janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro"
).split()
STATES = set(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)


def purchase_period(question: str) -> dict | None:
    text = normalize_temporal_text(question)
    match = re.search(r"\b(" + "|".join(MONTHS) + r")\s*(?:/|de\s+|\s)(\d{4}|\d{2})\b", text)
    if match:
        month = MONTHS.index(match.group(1)) + 1
        year = int(match.group(2))
        year = 2000 + year if year < 100 else year
        return {
            "type": "filter",
            "field": "dt_registro_mos",
            "operator": "date_between",
            "value": f"{year:04d}-{month:02d}-01",
            "end_value": f"{year:04d}-{month:02d}-{monthrange(year, month)[1]}",
        }
    return None


def ticket_geography(question: str) -> dict | None:
    text = normalize_temporal_text(question)
    match = re.search(
        r"\bticket\s+medio(?:\s+por\s+(?:compra|cliente))?\s+(?:de|da|do|em)\s+(.+?)(?=\s+(?:em|por)\s+|[?;!]|$)",
        text,
    )
    if not match:
        return None
    place = match.group(1).strip().strip('"“”')
    if re.match(
        r"(?:campanha|promocao|shopping|loja|segmento|restaurante|bairro|cada|todas?|todos?|\d)\b",
        place,
    ):
        return None
    state = re.sub(r"^(?:estado|uf)\s+(?:de\s+)?", "", place).upper()
    if state in STATES:
        return {"type": "filter", "field": "uf", "operator": "normalized_equals", "value": state}
    if place.startswith(("estado ", "uf ")):
        return {"type": "filter", "field": "uf", "operator": "normalized_equals", "value": state}
    place = re.sub(r"^cidade\s+(?:de\s+)?", "", place)
    return {"type": "filter", "field": "cidade", "operator": "normalized_equals", "value": place}


def is_customer_profile(question: str) -> bool:
    return bool(
        re.search(
            r"\bperfil\s+(?:dos?\s+)?(?:clientes|participantes)\b",
            normalize_temporal_text(question),
        )
    )

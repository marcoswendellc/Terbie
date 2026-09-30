import re
import unicodedata
from dataclasses import dataclass
from datetime import date


def normalize_temporal_text(text: str) -> str:
    return " ".join(
        "".join(
            character
            for character in unicodedata.normalize("NFKD", text.casefold())
            if not unicodedata.combining(character)
        ).split()
    )


@dataclass(frozen=True)
class TemporalSelection:
    field: str
    direction: str = "desc"
    limit: int = 1
    year: int | None = None
    active: bool = False

    @classmethod
    def parse(cls, question: str) -> "TemporalSelection | None":
        text = normalize_temporal_text(question)
        if not re.search(r"\b(campanhas?|promocoes|promocao)\b", text):
            return None
        if re.search(
            r"\b(faturamento|receita|ticket|vendeu|vendas?|compras?|clientes?|notas?|publico)\b",
            text,
        ):
            return None
        recent = re.search(r"\b(mais recentes?|recentemente|ultimas?|mais novas?)\b", text)
        oldest = re.search(r"\b(mais antigas?|primeiras?)\b", text)
        if not (recent or oldest):
            return None
        end = bool(re.search(r"\b(encerrad\w*|termin\w*|finaliz\w*|fim|sk_dtfim)\b", text))
        count = re.search(
            r"\b(?:top\s+|ultimas\s+|primeiras\s+|as\s+)?(\d+)\s+(?:campanhas|promocoes)\b", text
        )
        year = re.search(r"\b(?:19|20)\d{2}\b", text)
        return cls(
            field="sk_dtfim" if end else "sk_dtinicio",
            direction="asc" if oldest else "desc",
            limit=min(max(int(count.group(1)), 1), 100) if count else 1,
            year=int(year.group()) if year else None,
            active=bool(re.search(r"\b(ativas?|vigentes?|em andamento)\b", text)),
        )

    def clarification(self, question: str, filters: list[dict]) -> str | None:
        text = normalize_temporal_text(question)
        if re.search(
            r"\b(antes|depois|desde|entre|ontem|passad[oa]|futuras?|previstas?)\b"
            r"|\bate\b(?! hoje)|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}",
            text,
        ):
            return "Qual ano devo considerar para identificar a campanha?"
        shopping_scope = re.sub(r"\bem\s+qual\s+(?:shopping|empreendimento)\b", "", text)
        if re.search(
            r"\b(?:do|no|da|na|para|em)\s+(?:\w+\s+){0,4}(?:shopping|empreendimento)\b", shopping_scope
        ) and not any(item.get("field") == "nm_empreendimento" for item in filters):
            return "Não identifiquei o shopping solicitado. Qual é o nome completo?"
        return None

    @property
    def assumption(self) -> str:
        field = "término" if self.field == "sk_dtfim" else "início"
        order = "antiga" if self.direction == "asc" else "recente"
        return (
            f"Considero a data de {field} mais {order} até hoje ({date.today():%d/%m/%Y}). "
            "Campanhas com a mesma data são apresentadas como empate."
        )

    def parameters(self) -> dict[str, object]:
        return {
            "type": "temporal_order",
            "field": self.field,
            "direction": self.direction,
            "as_of": date.today().isoformat(),
            "year": self.year,
            "active": self.active,
        }


def is_campaign_listing(question: str) -> bool:
    text = normalize_temporal_text(question)
    return bool(
        re.search(r"\b(quais|liste|listar|mostre|mostrar)\b", text)
        and re.search(r"\b(campanhas|promocoes)\b", text)
        and not re.search(
            r"\b(compare|comparar|maior|menor|melhor|pior|faturamento|receita|ticket|compras|clientes|notas|performance)\b",
            text,
        )
    )


def resolve_temporal_reference(question: str, previous_question: str) -> str | None:
    """Restore the preceding question's scope only for a bare correction."""
    normalized = normalize_temporal_text(question).strip(" .!?")
    year_reference = re.fullmatch(r"e\s+(?:em\s+)?((?:19|20)\d{2})", normalized)
    if year_reference and is_campaign_listing(previous_question):
        # Replace a period, never a year embedded in a campaign name.
        return (
            re.sub(
                r"\b(em|de)\s+(?:19|20)\d{2}\b",
                lambda match: f"{match.group(1)} {year_reference.group(1)}",
                previous_question,
                flags=re.IGNORECASE,
            )
            if re.search(r"\b(?:em|de)\s+(?:19|20)\d{2}\b", previous_question, re.IGNORECASE)
            else None
        )
    if re.fullmatch(
        r"(?:e\s+)?qual\s+(?:foi\s+)?a\s+(?:mais\s+)?(?:recente|ultima|antiga)", normalized
    ):
        if TemporalSelection.parse(previous_question) is not None:
            if "antiga" in normalized:
                return re.sub(
                    r"mais\s+(?:recentes?|novas?)|recentemente|[úu]ltimas?",
                    "mais antiga",
                    previous_question,
                    flags=re.IGNORECASE,
                )
            if "recente" in normalized or "ultima" in normalized:
                return re.sub(
                    r"mais\s+antigas?|primeiras?",
                    "mais recente",
                    previous_question,
                    flags=re.IGNORECASE,
                )
            return previous_question
    return None

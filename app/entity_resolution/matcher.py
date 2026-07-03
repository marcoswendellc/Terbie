import re
import unicodedata
from difflib import SequenceMatcher

from app.entity_resolution.models import EntityCandidate, EntityMatch


class EntityMatcher:
    """Matches user text against registered business entity values."""

    _GENERIC_TOKENS = {
        "acao",
        "acoes",
        "campanha",
        "campanhas",
        "empreendimento",
        "empreendimentos",
        "loja",
        "lojas",
        "promocao",
        "promocoes",
        "segmento",
        "segmentos",
    }

    def match(self, *, query: str, candidate: EntityCandidate) -> EntityMatch | None:
        normalized_query = self.normalize(query)
        normalized_values = [
            self.normalize(value)
            for value in [candidate.value, *candidate.aliases]
        ]

        best_confidence = 0.0
        best_strategy = ""
        for normalized_value in normalized_values:
            confidence, strategy = self._score(
                normalized_query=normalized_query,
                normalized_value=normalized_value,
            )
            if confidence > best_confidence:
                best_confidence = confidence
                best_strategy = strategy

        if best_confidence < 0.78:
            return None

        return EntityMatch(
            field=candidate.field,
            value=candidate.value,
            entity_type=candidate.entity_type,
            confidence=round(best_confidence, 2),
            strategy=best_strategy,
        )

    def normalize(self, text: str) -> str:
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFKD", text.lower())
            if not unicodedata.combining(char)
        )
        alphanumeric_text = re.sub(r"[^a-z0-9]+", " ", without_accents)
        return re.sub(r"\s+", " ", alphanumeric_text).strip()

    def _score(self, *, normalized_query: str, normalized_value: str) -> tuple[float, str]:
        if normalized_query == normalized_value:
            return 1.0, "equals"

        compact_query = normalized_query.replace(" ", "")
        compact_value = normalized_value.replace(" ", "")
        if len(compact_value) < 4:
            pattern = rf"(?<!\w){re.escape(normalized_value)}(?!\w)"
            if re.search(pattern, normalized_query):
                return 0.98, "normalized_contains"

            return 0.0, ""

        if compact_value and compact_value in compact_query:
            return 0.98, "contains"

        if compact_query and compact_query in compact_value:
            return 0.94, "contains"

        value_tokens = [
            token
            for token in normalized_value.split()
            if len(token) >= 4 and not token.isdigit() and token not in self._GENERIC_TOKENS
        ]
        if value_tokens and any(token in normalized_query.split() for token in value_tokens):
            return 0.9, "normalized_contains"

        fuzzy_score = SequenceMatcher(None, compact_query, compact_value).ratio()
        if fuzzy_score >= 0.78:
            return fuzzy_score, "fuzzy"

        return 0.0, ""

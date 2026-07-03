from app.entity_resolution.matcher import EntityMatcher
from app.entity_resolution.models import (
    EntityCandidate,
    EntityMatch,
    EntityResolutionResult,
)


class EntityResolver:
    """Resolves partial mentions to registered Terral business entities."""

    _AMBIGUITY_DELTA = 0.05

    def __init__(
        self,
        *,
        candidates: list[EntityCandidate] | None = None,
        matcher: EntityMatcher | None = None,
    ) -> None:
        self._candidates = candidates or self._default_candidates()
        self._matcher = matcher or EntityMatcher()

    def resolve(self, question: str) -> EntityResolutionResult:
        matches = self._matches(question)
        if not matches:
            return EntityResolutionResult()

        matches = sorted(matches, key=lambda match: match.confidence, reverse=True)
        top_confidence = matches[0].confidence
        top_matches = [
            match
            for match in matches
            if top_confidence - match.confidence <= self._AMBIGUITY_DELTA
        ]

        if len(top_matches) > 1:
            return self._ambiguous_result(top_matches)

        return EntityResolutionResult(matches=[matches[0]])

    def resolve_many(self, question: str) -> EntityResolutionResult:
        matches = self._matches(question)
        if not matches:
            return EntityResolutionResult()

        by_field: dict[str, list[EntityMatch]] = {}
        for match in matches:
            by_field.setdefault(match.field, []).append(match)

        selected: list[EntityMatch] = []
        for field_matches in by_field.values():
            ordered_matches = sorted(
                field_matches,
                key=lambda match: match.confidence,
                reverse=True,
            )
            strong_matches = [match for match in ordered_matches if match.confidence >= 0.88]
            if not strong_matches:
                continue

            selected.extend(strong_matches)

        selected = self._deduplicate(selected)
        if len({match.value for match in selected}) < 2:
            return EntityResolutionResult(matches=selected)

        return EntityResolutionResult(matches=selected)

    def _matches(self, question: str) -> list[EntityMatch]:
        matches = [
            match
            for candidate in self._candidates
            if (match := self._matcher.match(query=question, candidate=candidate)) is not None
        ]
        return self._deduplicate(matches)

    def _ambiguous_result(self, matches: list[EntityMatch]) -> EntityResolutionResult:
        options = ", ".join(match.value for match in matches)
        return EntityResolutionResult(
            matches=matches,
            is_ambiguous=True,
            ambiguity_message=(
                "Encontrei mais de uma entidade possível: "
                f"{options}. Qual delas deseja utilizar?"
            ),
        )

    def _deduplicate(self, matches: list[EntityMatch]) -> list[EntityMatch]:
        deduplicated: dict[tuple[str, str], EntityMatch] = {}
        for match in matches:
            key = (match.field, match.value)
            current = deduplicated.get(key)
            if current is None or match.confidence > current.confidence:
                deduplicated[key] = match

        return list(deduplicated.values())

    def _default_candidates(self) -> list[EntityCandidate]:
        return [
            EntityCandidate(
                field="nm_promocao",
                value="Promoção Verão no Arca Parque 2026",
                entity_type="promocao",
                aliases=["arcaparque", "arca parque"],
            ),
            EntityCandidate(
                field="nm_promocao",
                value="No Pelo 360 com Hugo e Guilherme e Buriti Shopping",
                entity_type="promocao",
                aliases=["no pelo", "no pelo 360", "hugo e guilherme"],
            ),
            EntityCandidate(
                field="nm_fantasa",
                value="Camarada Camarão",
                entity_type="loja",
                aliases=["camarada", "camarada camarao"],
            ),
            EntityCandidate(
                field="nm_fantasa",
                value="C&A",
                entity_type="loja",
                aliases=["c&a", "cea"],
            ),
            EntityCandidate(
                field="nm_fantasa",
                value="O Boticário",
                entity_type="loja",
                aliases=["boticario", "o boticario"],
            ),
            EntityCandidate(
                field="nm_fantasa",
                value="Casas Bahia",
                entity_type="loja",
                aliases=["casas bahia"],
            ),
        ]

import re
import unicodedata
from dataclasses import dataclass

from app.semantic.entities import SEMANTIC_ENTITIES
from app.semantic.metrics import SEMANTIC_METRICS
from app.semantic.models import (
    SemanticEntity,
    SemanticMetric,
    SemanticParameter,
    SemanticParameterValue,
    SemanticResolution,
    SemanticTerm,
    SemanticTermSource,
    SemanticTermType,
)
from app.semantic.synonyms import BUSINESS_SYNONYMS


@dataclass(frozen=True, slots=True)
class _Alias:
    term: str
    normalized_term: str
    canonical: str
    type: SemanticTermType
    source: SemanticTermSource


class SemanticResolver:
    """Deterministic business vocabulary resolver for natural-language questions."""

    def __init__(self) -> None:
        self._aliases = self._build_aliases()

    def resolve(self, question: str) -> SemanticResolution:
        normalized_query = self.normalize(question)
        matched_terms = self._match_terms(normalized_query=normalized_query)
        parameters = self._extract_parameters(normalized_query=normalized_query)
        suggested_metrics = self._suggest_metrics(matched_terms)
        suggested_entities = self._suggest_entities(matched_terms)
        warnings = self._warnings(
            suggested_metrics=suggested_metrics,
            suggested_entities=suggested_entities,
        )
        confidence = self._confidence(
            matched_terms=matched_terms,
            parameters=parameters,
            warnings=warnings,
        )

        return SemanticResolution(
            original_query=question,
            normalized_query=normalized_query,
            matched_terms=matched_terms,
            parameters=parameters,
            warnings=warnings,
            confidence=confidence,
            suggested_metrics=suggested_metrics,
            suggested_entities=suggested_entities,
        )

    def normalize(self, text: str) -> str:
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFKD", text.lower())
            if not unicodedata.combining(char)
        )
        alphanumeric_text = re.sub(r"[^a-z0-9_]+", " ", without_accents)
        return re.sub(r"\s+", " ", alphanumeric_text).strip()

    def _build_aliases(self) -> list[_Alias]:
        aliases: list[_Alias] = []

        for canonical, synonyms in BUSINESS_SYNONYMS.items():
            term_type = self._type_for_canonical(canonical)
            aliases.append(
                _Alias(
                    term=canonical,
                    normalized_term=self.normalize(canonical),
                    canonical=canonical,
                    type=term_type,
                    source="canonical",
                ),
            )
            aliases.extend(
                _Alias(
                    term=synonym,
                    normalized_term=self.normalize(synonym),
                    canonical=canonical,
                    type=term_type,
                    source=(
                        "canonical"
                        if self.normalize(synonym) == self.normalize(canonical)
                        else "synonym"
                    ),
                )
                for synonym in synonyms
            )

        return sorted(
            aliases,
            key=lambda alias: (len(alias.normalized_term), alias.normalized_term),
            reverse=True,
        )

    def _type_for_canonical(self, canonical: str) -> SemanticTermType:
        if canonical in SEMANTIC_METRICS:
            return "metric"

        if canonical in SEMANTIC_ENTITIES:
            return "entity"

        if canonical == "ranking":
            return "intent"

        return "concept"

    def _match_terms(self, *, normalized_query: str) -> list[SemanticTerm]:
        matches: list[SemanticTerm] = []
        seen: set[tuple[str, str, SemanticTermType]] = set()

        for alias in self._aliases:
            pattern = rf"(?<!\w){re.escape(alias.normalized_term)}(?!\w)"
            if not re.search(pattern, normalized_query):
                continue

            key = (alias.term, alias.canonical, alias.type)
            if key in seen:
                continue

            seen.add(key)
            matches.append(
                SemanticTerm(
                    term=alias.term,
                    canonical=alias.canonical,
                    type=alias.type,
                    confidence=1.0,
                    source=alias.source,
                ),
            )

        return matches

    def _extract_parameters(self, *, normalized_query: str) -> list[SemanticParameter]:
        parameters: list[SemanticParameter] = []
        parameters.extend(self._extract_limit_parameters(normalized_query=normalized_query))
        parameters.extend(self._extract_period_parameters(normalized_query=normalized_query))
        return self._deduplicate_parameters(parameters)

    def _extract_limit_parameters(self, *, normalized_query: str) -> list[SemanticParameter]:
        parameters: list[SemanticParameter] = []
        patterns = [
            r"(?<!\w)top\s+(?P<value>\d+)(?!\w)",
            r"(?<!\w)(?P<value>\d+)\s+(maior|maiores|melhor|melhores|menor|menores)(?!\w)",
            r"(?<!\w)(?P<value>\d+)\s+(restaurante|restaurantes|loja|lojas|cliente|clientes|shopping|shoppings)(?!\w)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, normalized_query):
                parameters.append(
                    SemanticParameter(
                        type="limit",
                        value=int(match.group("value")),
                        term=match.group(0),
                        confidence=1.0,
                    ),
                )

        return parameters

    def _extract_period_parameters(self, *, normalized_query: str) -> list[SemanticParameter]:
        period_patterns: dict[str, str] = {
            r"(?<!\w)ultimos\s+30\s+dias(?!\w)": "last_30_days",
            r"(?<!\w)este\s+mes(?!\w)": "current_month",
            r"(?<!\w)ano\s+passado(?!\w)": "last_year",
        }
        parameters: list[SemanticParameter] = []

        for pattern, value in period_patterns.items():
            for match in re.finditer(pattern, normalized_query):
                parameters.append(
                    SemanticParameter(
                        type="period",
                        value=value,
                        term=match.group(0),
                        confidence=1.0,
                    ),
                )

        for match in re.finditer(r"(?<!\w)(?P<value>20\d{2})(?!\w)", normalized_query):
            parameters.append(
                SemanticParameter(
                    type="period",
                    value=match.group("value"),
                    term=match.group(0),
                    confidence=1.0,
                ),
            )

        return parameters

    def _deduplicate_parameters(
        self,
        parameters: list[SemanticParameter],
    ) -> list[SemanticParameter]:
        deduplicated: list[SemanticParameter] = []
        seen: set[tuple[str, SemanticParameterValue]] = set()

        for parameter in parameters:
            key = (parameter.type, parameter.value)
            if key in seen:
                continue

            deduplicated.append(parameter)
            seen.add(key)

        return deduplicated

    def _suggest_metrics(self, matched_terms: list[SemanticTerm]) -> list[SemanticMetric]:
        metrics: list[SemanticMetric] = []
        seen: set[str] = set()

        for term in matched_terms:
            metric = SEMANTIC_METRICS.get(term.canonical)
            if metric is None or metric.name in seen:
                continue

            metrics.append(metric)
            seen.add(metric.name)

        return metrics

    def _suggest_entities(self, matched_terms: list[SemanticTerm]) -> list[SemanticEntity]:
        entities: list[SemanticEntity] = []
        seen: set[str] = set()

        for term in matched_terms:
            entity = SEMANTIC_ENTITIES.get(term.canonical)
            if entity is None or entity.name in seen:
                continue

            entities.append(entity)
            seen.add(entity.name)

        return entities

    def _warnings(
        self,
        *,
        suggested_metrics: list[SemanticMetric],
        suggested_entities: list[SemanticEntity],
    ) -> list[str]:
        warnings: list[str] = []

        if not suggested_metrics:
            warnings.append("Nenhuma métrica encontrada.")

        if len(suggested_entities) > 1:
            warnings.append("Mais de uma entidade encontrada.")

        return warnings

    def _confidence(
        self,
        *,
        matched_terms: list[SemanticTerm],
        parameters: list[SemanticParameter],
        warnings: list[str],
    ) -> float:
        relevant_terms = max(len(matched_terms) + len(parameters) + len(warnings), 1)
        confidence = (len(matched_terms) + len(parameters)) / relevant_terms
        return round(min(confidence, 1.0), 2)

import re
import unicodedata
from dataclasses import dataclass

from app.semantic.dictionary import SEMANTIC_DICTIONARY
from app.semantic.entities import SEMANTIC_ENTITIES
from app.semantic.metrics import SEMANTIC_METRICS
from app.semantic.models import (
    SemanticEntity,
    SemanticInterpretation,
    SemanticMappedColumn,
    SemanticMetric,
    SemanticParameter,
    SemanticParameterValue,
    SemanticResolution,
    SemanticTerm,
    SemanticTermSource,
    SemanticTermType,
)
from app.semantic.response_rules import SEMANTIC_RESPONSE_RULES
from app.semantic.synonyms import BUSINESS_SYNONYMS, USER_TERM_COLUMN_MAP

SEMANTIC_INTENTS = SEMANTIC_DICTIONARY["intents"]


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
        mapped_columns = self._mapped_columns(
            matched_terms=matched_terms,
            normalized_query=normalized_query,
        )
        interpretation = self._interpretation(
            normalized_query=normalized_query,
            suggested_metrics=suggested_metrics,
            suggested_entities=suggested_entities,
            parameters=parameters,
        )
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
            mapped_columns=mapped_columns,
            interpretation=interpretation,
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

        if isinstance(SEMANTIC_INTENTS, dict) and canonical in SEMANTIC_INTENTS:
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

    def _mapped_columns(
        self,
        *,
        matched_terms: list[SemanticTerm],
        normalized_query: str,
    ) -> list[SemanticMappedColumn]:
        mapped_columns: list[SemanticMappedColumn] = []
        seen: set[tuple[str, str]] = set()

        for term in matched_terms:
            column: str | list[str] | None = None
            role: str = "dimension"
            metric = SEMANTIC_METRICS.get(term.canonical)
            entity = SEMANTIC_ENTITIES.get(term.canonical)
            if metric is not None and metric.column is not None:
                column = metric.column
                role = "metric"
            elif entity is not None and entity.column is not None:
                column = entity.column

            if column is None:
                continue

            key = (term.canonical, str(column))
            if key in seen:
                continue

            mapped_columns.append(
                SemanticMappedColumn(
                    term=term.term,
                    canonical=term.canonical,
                    column=column,
                    role=role,  # type: ignore[arg-type]
                ),
            )
            seen.add(key)

        for user_term, column in USER_TERM_COLUMN_MAP.items():
            normalized_term = self.normalize(user_term)
            pattern = rf"(?<!\w){re.escape(normalized_term)}(?!\w)"
            if not re.search(pattern, normalized_query):
                continue

            key = (user_term, str(column))
            if key in seen:
                continue

            mapped_columns.append(
                SemanticMappedColumn(
                    term=user_term,
                    canonical=user_term,
                    column=column,
                    role="date" if isinstance(column, list) else "dimension",
                ),
            )
            seen.add(key)

        return mapped_columns

    def _interpretation(
        self,
        *,
        normalized_query: str,
        suggested_metrics: list[SemanticMetric],
        suggested_entities: list[SemanticEntity],
        parameters: list[SemanticParameter],
    ) -> SemanticInterpretation | None:
        intent = self._intent(normalized_query=normalized_query, entities=suggested_entities)
        entity = self._primary_entity(
            suggested_entities=suggested_entities,
            normalized_query=normalized_query,
        )
        metrics = self._resolved_metric_names(
            suggested_metrics,
            normalized_query=normalized_query,
        )
        if intent is None and metrics:
            intent = "metric_query"
        dimensions = self._dimensions_for(entity=entity, intent=intent)
        filters = self._semantic_filters(
            entity=entity,
            parameters=parameters,
        )
        operation = self._operation_for_intent(intent)
        response_rule_ids = self._response_rule_ids(intent=intent, entity=entity)

        if not any([intent, entity, metrics, dimensions, filters, response_rule_ids]):
            return None

        return SemanticInterpretation(
            intent=intent,
            entity=entity,
            operation=operation,
            metrics=metrics,
            dimensions=dimensions,
            filters=filters,
            response_rule_ids=response_rule_ids,
        )

    def _intent(
        self,
        *,
        normalized_query: str,
        entities: list[SemanticEntity],
    ) -> str | None:
        has_promotion = any(entity.name == "promocao" for entity in entities)
        if has_promotion and self._matches_any(
            normalized_query,
            [
                r"\b(detalhar|detalhe|detalha)\b",
                r"\bresumo\b",
                r"\bcomo\s+foi\b",
            ],
        ):
            return "campaign_detail"

        if self._matches_any(
            normalized_query,
            [r"\bcomparar\b", r"\bcomparativo\b", r"\bversus\b", r"\bvs\b", r"\bcontra\b"],
        ):
            return "comparison"

        if self._matches_any(
            normalized_query,
            [r"\bresumo\b", r"\bresumir\b", r"\bdetalhe\b", r"\bdetalhar\b"],
        ):
            return "summary"

        if has_promotion and self._matches_any(
            normalized_query,
            [
                r"\bquais\s+(campanhas|promocoes|acoes)\b",
                r"\bliste\s+(as\s+)?(campanhas|promocoes|acoes)\b",
                r"\b(campanhas|promocoes|acoes)\s+ocorreram\b",
            ],
        ):
            return "list_distinct"

        if self._matches_any(
            normalized_query,
            [r"\branking\b", r"\btop\b", r"\bmaior\b", r"\bmaiores\b", r"\bmelhor\b"],
        ):
            return "ranking"

        return None

    def _resolved_metric_names(
        self,
        metrics: list[SemanticMetric],
        *,
        normalized_query: str,
    ) -> list[str]:
        resolved: list[str] = []
        seen: set[str] = set()
        ordered_metrics = sorted(
            metrics,
            key=lambda metric: self._metric_position(metric, normalized_query=normalized_query),
        )
        for metric in ordered_metrics:
            metric_names = metric.expands_to or [metric.equivalent_to or metric.name]
            for metric_name in metric_names:
                if metric_name in seen:
                    continue

                resolved.append(metric_name)
                seen.add(metric_name)

        return resolved

    def _metric_position(self, metric: SemanticMetric, *, normalized_query: str) -> int:
        positions = [
            normalized_query.find(self.normalize(term))
            for term in [metric.name, *metric.synonyms]
            if self.normalize(term) in normalized_query
        ]
        valid_positions = [position for position in positions if position >= 0]
        return min(valid_positions) if valid_positions else len(normalized_query)

    def _matches_any(self, text: str, patterns: list[str]) -> bool:
        return any(re.search(pattern, text) for pattern in patterns)

    def _primary_entity(
        self,
        *,
        suggested_entities: list[SemanticEntity],
        normalized_query: str,
    ) -> str | None:
        entity_names = {entity.name for entity in suggested_entities}
        if "promocao" in entity_names or self._matches_any(
            normalized_query,
            [r"\bcampanha\b", r"\bcampanhas\b", r"\bpromocao\b", r"\bpromocoes\b"],
        ):
            return "promocao"

        return suggested_entities[0].name if suggested_entities else None

    def _dimensions_for(self, *, entity: str | None, intent: str | None) -> list[str]:
        if entity is None:
            return []

        semantic_entity = SEMANTIC_ENTITIES.get(entity)
        if semantic_entity is None or semantic_entity.column is None:
            return []

        if intent in {"list_distinct", "comparison", "summary", "ranking", "campaign_detail"}:
            return [semantic_entity.column]

        return []

    def _semantic_filters(
        self,
        *,
        entity: str | None,
        parameters: list[SemanticParameter],
    ) -> list[dict[str, object]]:
        filters: list[dict[str, object]] = []
        if entity == "promocao":
            filters.append(
                {
                    "type": "filter",
                    "field": "cd_promocao",
                    "operator": "not_null",
                    "source": "semantic_dictionary",
                },
            )

        for parameter in parameters:
            if parameter.type != "period" or not str(parameter.value).isdigit():
                continue

            if entity == "promocao":
                filters.append(
                    {
                        "type": "filter",
                        "field": "sk_dtinicio",
                        "operator": "year_overlap",
                        "value": int(parameter.value),
                        "end_field": "sk_dtfim",
                        "source": "semantic_dictionary",
                    },
                )
            else:
                filters.append(
                    {
                        "type": "period",
                        "value": parameter.value,
                        "source": "semantic_dictionary",
                    },
                )

        return filters

    def _operation_for_intent(self, intent: str | None) -> str | None:
        if intent is None or not isinstance(SEMANTIC_INTENTS, dict):
            return None

        intent_definition = SEMANTIC_INTENTS.get(intent)
        if not isinstance(intent_definition, dict):
            return None

        operation = intent_definition.get("operation")
        return operation if isinstance(operation, str) else None

    def _response_rule_ids(self, *, intent: str | None, entity: str | None) -> list[str]:
        rule_ids: list[str] = []
        for rule_id, rule in SEMANTIC_RESPONSE_RULES.items():
            if rule.get("intent") != intent:
                continue
            if rule.get("entity") is not None and rule.get("entity") != entity:
                continue
            rule_ids.append(rule_id)

        return rule_ids

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

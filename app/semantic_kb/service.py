from functools import lru_cache
from typing import Any

from app.knowledge.models import BusinessDimension, BusinessEntity, BusinessMetric, BusinessRule
from app.semantic_kb.data import SEMANTIC_KNOWLEDGE_BASE
from app.semantic_kb.models import (
    KBDimension,
    KBMetric,
    SemanticKnowledgeBase,
)


class SemanticKnowledgeBaseService:
    """Provides projections of Terbie's canonical semantic knowledge base."""

    def __init__(self, knowledge_base: SemanticKnowledgeBase | None = None) -> None:
        self._knowledge_base = knowledge_base or SEMANTIC_KNOWLEDGE_BASE

    @property
    def knowledge_base(self) -> SemanticKnowledgeBase:
        return self._knowledge_base

    def as_semantic_dictionary(self) -> dict[str, object]:
        return {
            "version": self._knowledge_base.version,
            "metrics": {
                metric.name: self._metric_definition(metric)
                for metric in self._knowledge_base.metrics
            },
            "dimensions": {
                dimension.name: self._dimension_definition(dimension)
                for dimension in self._knowledge_base.dimensions
            },
            "intents": {
                intent.name: {
                    "operation": intent.operation,
                    "synonyms": intent.synonyms,
                    "priority": intent.priority,
                    "response_rule_ids": intent.response_rule_ids,
                }
                for intent in self._knowledge_base.intents
            },
            "column_mappings": dict(self._knowledge_base.column_mappings),
        }

    def business_metrics(self) -> list[BusinessMetric]:
        metrics: list[BusinessMetric] = []
        for metric in self._knowledge_base.metrics:
            metrics.append(
                BusinessMetric(
                    name=metric.name,
                    column=metric.column,
                    aggregation=metric.operation,
                    formula=metric.formula,
                    synonyms=metric.synonyms,
                ),
            )
        return metrics

    def business_dimensions(self) -> list[BusinessDimension]:
        dimensions: list[BusinessDimension] = []
        for dimension in self._knowledge_base.dimensions:
            dimensions.append(
                BusinessDimension(
                    name=dimension.name,
                    column=dimension.column,
                    key=dimension.key,
                    derived_from=dimension.derived_from,
                    derivation_rule=dimension.derivation_rule,
                ),
            )
        return dimensions

    def business_rules(self) -> list[BusinessRule]:
        return [
            BusinessRule(
                code=rule.id,
                description=rule.description,
                fields=rule.fields,
                concepts=rule.concepts,
            )
            for rule in self._knowledge_base.business_rules
        ]

    def business_entities(self) -> list[BusinessEntity]:
        entities: list[BusinessEntity] = []
        for dimension in self._knowledge_base.dimensions:
            fields = [
                field
                for field in [dimension.key, dimension.column, *dimension.date_fields]
                if field is not None
            ]
            entities.append(
                BusinessEntity(
                    name=dimension.name,
                    fields=self._deduplicate(fields),
                    description=f"Entidade semantica {dimension.name}.",
                ),
            )
        return entities

    def examples(self) -> list[dict[str, Any]]:
        return [example.model_dump() for example in self._knowledge_base.examples]

    def response_rules(self) -> dict[str, dict[str, object]]:
        return {
            rule.id: {
                "intent": rule.intent,
                "entity": rule.entity,
                "description": rule.description,
                "must_include": rule.must_include,
                "must_not_include": rule.must_not_include,
                "suggestions": rule.suggestions,
                "priority": rule.priority,
            }
            for rule in self._knowledge_base.response_rules
        }

    def _metric_definition(self, metric: KBMetric) -> dict[str, object]:
        return {
            "operation": metric.operation,
            "column": metric.column,
            "formula": metric.formula,
            "synonyms": metric.synonyms,
            "priority": metric.priority,
            "contexts": metric.contexts,
            "equivalent_to": metric.equivalent_to,
            "expands_to": metric.expands_to,
            "ambiguity_policy": metric.ambiguity_policy,
        }

    def _dimension_definition(self, dimension: KBDimension) -> dict[str, object]:
        return {
            "column": dimension.column,
            "key": dimension.key,
            "derived_from": dimension.derived_from,
            "derivation_rule": dimension.derivation_rule,
            "date_fields": dimension.date_fields,
            "synonyms": dimension.synonyms,
            "priority": dimension.priority,
            "contexts": dimension.contexts,
        }

    def _deduplicate(self, values: list[str]) -> list[str]:
        deduplicated: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value in seen:
                continue
            deduplicated.append(value)
            seen.add(value)
        return deduplicated


@lru_cache
def get_semantic_kb() -> SemanticKnowledgeBaseService:
    return SemanticKnowledgeBaseService()

from app.knowledge.business_rules import BUSINESS_RULES
from app.knowledge.calendars import BUSINESS_CALENDARS
from app.knowledge.dimensions import BUSINESS_DIMENSIONS
from app.knowledge.hierarchy import BUSINESS_HIERARCHIES
from app.knowledge.metrics import BUSINESS_METRICS
from app.knowledge.models import (
    BusinessCalendar,
    BusinessDimension,
    BusinessEntity,
    BusinessHierarchy,
    BusinessMetric,
    BusinessRule,
    BusinessTaxonomy,
    KnowledgeContext,
)
from app.knowledge.ontology import BUSINESS_ENTITIES
from app.knowledge.taxonomy import BUSINESS_TAXONOMIES
from app.semantic_kb import SemanticKnowledgeBaseService, get_semantic_kb


class KnowledgeService:
    """Provides Terral business knowledge as structured metadata."""

    def __init__(self, semantic_kb: SemanticKnowledgeBaseService | None = None) -> None:
        self._semantic_kb = semantic_kb or get_semantic_kb()

    def get_context(self) -> KnowledgeContext:
        return KnowledgeContext(
            entities=self.get_entities(),
            metrics=self.get_metrics(),
            dimensions=self.get_dimensions(),
            rules=self.get_rules(),
            hierarchies=self.get_hierarchies(),
            calendars=self.get_calendars(),
            taxonomies=self.get_taxonomies(),
        )

    def get_metrics(self) -> list[BusinessMetric]:
        return self._merge_by_name(self._semantic_kb.business_metrics(), BUSINESS_METRICS)

    def get_dimensions(self) -> list[BusinessDimension]:
        return self._merge_by_name(self._semantic_kb.business_dimensions(), BUSINESS_DIMENSIONS)

    def get_rules(self) -> list[BusinessRule]:
        return self._merge_by_code(self._semantic_kb.business_rules(), BUSINESS_RULES)

    def get_entities(self) -> list[BusinessEntity]:
        return self._merge_by_name(self._semantic_kb.business_entities(), BUSINESS_ENTITIES)

    def get_calendars(self) -> list[BusinessCalendar]:
        return BUSINESS_CALENDARS

    def get_taxonomies(self) -> list[BusinessTaxonomy]:
        return BUSINESS_TAXONOMIES

    def get_hierarchies(self) -> list[BusinessHierarchy]:
        return BUSINESS_HIERARCHIES

    def _merge_by_name(self, primary, compatibility):
        merged = list(primary)
        seen = {item.name for item in merged}
        for item in compatibility:
            if item.name in seen:
                continue
            merged.append(item)
            seen.add(item.name)
        return merged

    def _merge_by_code(
        self,
        primary: list[BusinessRule],
        compatibility: list[BusinessRule],
    ) -> list[BusinessRule]:
        merged = list(primary)
        seen = {item.code for item in merged}
        for item in compatibility:
            if item.code in seen:
                continue
            merged.append(item)
            seen.add(item.code)
        return merged

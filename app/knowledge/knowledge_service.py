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


class KnowledgeService:
    """Provides Terral business knowledge as structured metadata."""

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
        return BUSINESS_METRICS

    def get_dimensions(self) -> list[BusinessDimension]:
        return BUSINESS_DIMENSIONS

    def get_rules(self) -> list[BusinessRule]:
        return BUSINESS_RULES

    def get_entities(self) -> list[BusinessEntity]:
        return BUSINESS_ENTITIES

    def get_calendars(self) -> list[BusinessCalendar]:
        return BUSINESS_CALENDARS

    def get_taxonomies(self) -> list[BusinessTaxonomy]:
        return BUSINESS_TAXONOMIES

    def get_hierarchies(self) -> list[BusinessHierarchy]:
        return BUSINESS_HIERARCHIES

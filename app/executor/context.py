from dataclasses import dataclass, field
from typing import Any

from app.knowledge.models import KnowledgeContext


@dataclass(slots=True)
class ExecutionContext:
    knowledge_context: KnowledgeContext
    group_by_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def resolve_dimension_column(self, name: str | None) -> str | None:
        if name is None:
            return None

        for dimension in self.knowledge_context.dimensions:
            if dimension.name == name:
                return dimension.column or dimension.key or dimension.derived_from or name

        return name

    def resolve_metric_column(self, name: str | None) -> str | None:
        if name is None:
            return None

        for metric in self.knowledge_context.metrics:
            if metric.name == name:
                return metric.column

        return name

    def metric_formula(self, name: str | None) -> str | None:
        if name is None:
            return None

        for metric in self.knowledge_context.metrics:
            if metric.name == name:
                return metric.formula

        return None

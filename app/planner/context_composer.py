from typing import Any

from app.catalog.data_catalog import DataCatalog
from app.knowledge.models import KnowledgeContext
from app.reasoning.models import ReasoningContext
from app.semantic.models import SemanticResolution


class PlannerContextComposer:
    """Composes safe structured context for a reasoning provider."""

    def compose(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution,
        schema: dict[str, Any] | None = None,
        data_catalog: DataCatalog | None = None,
        knowledge_context: KnowledgeContext | None = None,
    ) -> ReasoningContext:
        return ReasoningContext(
            question=question,
            semantic_resolution=semantic_resolution,
            schema_context=schema,
            catalog_context=self._catalog_context(data_catalog),
            knowledge_context=knowledge_context,
        )

    def _catalog_context(self, data_catalog: DataCatalog | None) -> dict[str, Any] | None:
        if data_catalog is None:
            return None

        return {
            "tables": [
                {
                    "name": table_name,
                    "schema": data_catalog.get_schema(table_name).model_dump(mode="json")
                    if data_catalog.get_schema(table_name) is not None
                    else None,
                }
                for table_name in data_catalog.list_tables()
            ],
        }

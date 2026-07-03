from app.compiler.models import AnalyticalHypothesis, AnalyticalPlan
from app.knowledge.business_defaults import PROMOTION_COMPARISON_METRICS
from app.knowledge.models import KnowledgeContext


class AnalyticalPlanner:
    """Converts an analytical hypothesis into an intermediate analytical plan."""

    def build(
        self,
        *,
        hypothesis: AnalyticalHypothesis,
        knowledge_context: KnowledgeContext | None = None,
    ) -> AnalyticalPlan:
        metrics = self._metrics(hypothesis)
        entities = [hypothesis.business_entity] if hypothesis.business_entity is not None else []
        dimensions = self._dimensions(
            analysis_type=hypothesis.analysis_type,
            business_entity=hypothesis.business_entity,
            knowledge_context=knowledge_context,
        )

        return AnalyticalPlan(
            intent=hypothesis.analysis_type,
            entities=entities,
            metrics=metrics,
            dimensions=dimensions,
            time_scope=hypothesis.time_scope,
            filters=self._filters(hypothesis),
            comparison_entities=hypothesis.comparison_entities,
            required_operations=self._required_operations(
                analysis_type=hypothesis.analysis_type,
                business_entity=hypothesis.business_entity,
                filters=self._filters(hypothesis),
            ),
            warnings=hypothesis.warnings,
        )

    def _required_operations(
        self,
        *,
        analysis_type: str | None,
        business_entity: str | None,
        filters: list[dict[str, object]],
    ) -> list[str]:
        filter_operations = ["filter"] if self._has_executable_filters(filters) else []

        if analysis_type == "ranking":
            return [*filter_operations, "group_by", "aggregate", "sort", "limit"]

        if analysis_type == "comparison":
            return [*filter_operations, "group_by", "aggregate", "derived_metric", "sort"]

        if analysis_type == "list_distinct":
            return [*filter_operations, "select", "distinct", "sort"]

        if business_entity is not None:
            return [*filter_operations, "group_by", "aggregate"]

        return [*filter_operations, "aggregate"]

    def _dimensions(
        self,
        *,
        analysis_type: str | None,
        business_entity: str | None,
        knowledge_context: KnowledgeContext | None,
    ) -> list[str]:
        available_dimensions = {
            dimension.name for dimension in knowledge_context.dimensions
        } if knowledge_context is not None else set()

        if analysis_type == "comparison" and business_entity == "promocao":
            return ["nm_promocao"]

        if business_entity == "restaurante":
            if "loja" in available_dimensions:
                return ["loja"]
            if "segmento" in available_dimensions:
                return ["segmento"]

        if business_entity == "loja":
            return ["loja"]

        if business_entity == "empreendimento":
            return ["empreendimento"]

        if business_entity == "segmento":
            return ["segmento"]

        if business_entity == "promocao":
            return ["promocao"]

        return []

    def _metrics(self, hypothesis: AnalyticalHypothesis) -> list[str]:
        if hypothesis.analysis_type == "comparison" and hypothesis.business_entity == "promocao":
            return [metric.name for metric in PROMOTION_COMPARISON_METRICS]

        return [hypothesis.metric] if hypothesis.metric is not None else []

    def _filters(self, hypothesis: AnalyticalHypothesis) -> list[dict[str, object]]:
        filters = list(hypothesis.filters)

        if hypothesis.business_entity == "restaurante":
            restaurant_filter = {
                "type": "filter",
                "field": "segmento",
                "operator": "contains",
                "value": "Alimentação",
            }
            if restaurant_filter not in filters:
                filters.insert(0, restaurant_filter)

        if hypothesis.business_entity == "promocao":
            promotion_key_filter = {
                "type": "filter",
                "field": "cd_promocao",
                "operator": "not_null",
            }
            if promotion_key_filter not in filters:
                filters.insert(0, promotion_key_filter)

            if hypothesis.time_scope is not None and hypothesis.time_scope.isdigit():
                promotion_year_filter = {
                    "type": "filter",
                    "field": "sk_dtinicio",
                    "operator": "year_overlap",
                    "value": int(hypothesis.time_scope),
                    "end_field": "sk_dtfim",
                }
                if promotion_year_filter not in filters:
                    filters.append(promotion_year_filter)

        if hypothesis.analysis_type == "comparison" and hypothesis.comparison_entities:
            field = hypothesis.comparison_entities[0].get("field")
            values = [
                entity.get("value")
                for entity in hypothesis.comparison_entities
                if isinstance(entity.get("value"), str)
            ]
            if isinstance(field, str) and values:
                comparison_filter = {
                    "type": "filter",
                    "field": field,
                    "operator": "in",
                    "value": values,
                }
                if comparison_filter not in filters:
                    filters.append(comparison_filter)

        return filters

    def _has_executable_filters(self, filters: list[dict[str, object]]) -> bool:
        return any(filter_item.get("type") == "filter" for filter_item in filters)

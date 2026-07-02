from app.compiler.models import AnalyticalHypothesis, AnalyticalPlan
from app.knowledge.models import KnowledgeContext


class AnalyticalPlanner:
    """Converts an analytical hypothesis into an intermediate analytical plan."""

    def build(
        self,
        *,
        hypothesis: AnalyticalHypothesis,
        knowledge_context: KnowledgeContext | None = None,
    ) -> AnalyticalPlan:
        metrics = [hypothesis.metric] if hypothesis.metric is not None else []
        entities = [hypothesis.business_entity] if hypothesis.business_entity is not None else []
        dimensions = self._dimensions(
            business_entity=hypothesis.business_entity,
            knowledge_context=knowledge_context,
        )

        return AnalyticalPlan(
            intent=hypothesis.analysis_type,
            entities=entities,
            metrics=metrics,
            dimensions=dimensions,
            time_scope=hypothesis.time_scope,
            filters=hypothesis.filters,
            required_operations=self._required_operations(
                analysis_type=hypothesis.analysis_type,
                business_entity=hypothesis.business_entity,
            ),
            warnings=hypothesis.warnings,
        )

    def _required_operations(
        self,
        *,
        analysis_type: str | None,
        business_entity: str | None,
    ) -> list[str]:
        if analysis_type == "ranking":
            return ["group_by", "aggregate", "sort", "limit"]

        if business_entity is not None:
            return ["group_by", "aggregate"]

        return ["aggregate"]

    def _dimensions(
        self,
        *,
        business_entity: str | None,
        knowledge_context: KnowledgeContext | None,
    ) -> list[str]:
        available_dimensions = {
            dimension.name for dimension in knowledge_context.dimensions
        } if knowledge_context is not None else set()

        if business_entity == "restaurante":
            if "loja" in available_dimensions:
                return ["loja"]
            if "segmento" in available_dimensions:
                return ["segmento"]

        if business_entity == "loja":
            return ["loja"]

        return []

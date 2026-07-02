from typing import Any

from app.compiler.models import AnalyticalHypothesis
from app.knowledge.models import KnowledgeContext
from app.semantic.models import SemanticResolution


class HypothesisBuilder:
    """Builds the first analytical hypothesis from semantic and knowledge context."""

    def build(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution | None,
        knowledge_context: KnowledgeContext | None = None,
    ) -> AnalyticalHypothesis:
        _ = question, knowledge_context
        warnings: list[str] = []
        analysis_type = self._analysis_type(semantic_resolution)
        metric = self._metric(semantic_resolution)
        business_entity = self._business_entity(semantic_resolution)
        time_scope = self._time_scope(semantic_resolution)

        if metric is None:
            warnings.append("Nenhuma métrica identificada.")

        if business_entity is None:
            warnings.append("Nenhuma entidade de negócio identificada.")

        return AnalyticalHypothesis(
            goal="identificar melhores resultados" if analysis_type == "ranking" else None,
            analysis_type=analysis_type,
            business_entity=business_entity,
            metric=metric,
            time_scope=time_scope,
            filters=self._filters(semantic_resolution),
            confidence=self._confidence(
                analysis_type=analysis_type,
                metric=metric,
                business_entity=business_entity,
            ),
            warnings=warnings,
        )

    def _analysis_type(self, semantic_resolution: SemanticResolution | None) -> str | None:
        if semantic_resolution is None:
            return None

        if any(term.canonical == "ranking" for term in semantic_resolution.matched_terms):
            return "ranking"

        return None

    def _filters(
        self,
        semantic_resolution: SemanticResolution | None,
    ) -> list[dict[str, Any]]:
        if semantic_resolution is None:
            return []

        return [
            {"type": parameter.type, "value": parameter.value}
            for parameter in semantic_resolution.parameters
            if parameter.type in {"limit", "period", "comparison", "order"}
        ]

    def _metric(self, semantic_resolution: SemanticResolution | None) -> str | None:
        if semantic_resolution is None:
            return None

        metric_names = {metric.name for metric in semantic_resolution.suggested_metrics}
        if "faturamento" in metric_names:
            return "faturamento"

        if "ticket_medio" in metric_names:
            return "ticket_medio"

        return None

    def _business_entity(self, semantic_resolution: SemanticResolution | None) -> str | None:
        if semantic_resolution is None:
            return None

        entity_names = {entity.name for entity in semantic_resolution.suggested_entities}
        if "restaurante" in entity_names:
            return "restaurante"

        if "loja" in entity_names:
            return "loja"

        return None

    def _time_scope(self, semantic_resolution: SemanticResolution | None) -> str | None:
        if semantic_resolution is None:
            return None

        for parameter in semantic_resolution.parameters:
            if parameter.type == "period" and isinstance(parameter.value, str):
                return parameter.value

        return None

    def _confidence(
        self,
        *,
        analysis_type: str | None,
        metric: str | None,
        business_entity: str | None,
    ) -> float:
        signals: list[Any | None] = [analysis_type, metric, business_entity]
        return round(sum(signal is not None for signal in signals) / len(signals), 2)

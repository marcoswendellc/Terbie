import re
import unicodedata
from typing import Any

from app.compiler.models import AnalyticalHypothesis
from app.knowledge.models import KnowledgeContext
from app.metrics.metric_resolver import MetricResolver
from app.semantic.models import SemanticResolution


class HypothesisBuilder:
    """Builds the first analytical hypothesis from semantic and knowledge context."""

    def __init__(self, metric_resolver: MetricResolver | None = None) -> None:
        self._metric_resolver = metric_resolver or MetricResolver()

    def build(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution | None,
        knowledge_context: KnowledgeContext | None = None,
    ) -> AnalyticalHypothesis:
        _ = knowledge_context
        warnings: list[str] = []
        analysis_type = self._analysis_type(
            question=question,
            semantic_resolution=semantic_resolution,
        )
        metric, metric_source = self._metric(
            question=question,
            analysis_type=analysis_type,
            semantic_resolution=semantic_resolution,
        )
        business_entity = self._business_entity(semantic_resolution)
        metrics = self._metrics(metric=metric, semantic_resolution=semantic_resolution)
        time_scope = self._time_scope(semantic_resolution)

        if not metrics and metric is None and analysis_type not in {
            "campaign_detail",
            "list_distinct",
            "comparison",
            "summary",
        }:
            warnings.append("Nenhuma métrica identificada.")

        if business_entity is None:
            warnings.append("Nenhuma entidade de negócio identificada.")

        return AnalyticalHypothesis(
            goal="identificar melhores resultados" if analysis_type == "ranking" else None,
            analysis_type=analysis_type,
            business_entity=business_entity,
            metric=metric,
            metrics=metrics,
            metric_source=metric_source,
            time_scope=time_scope,
            filters=self._filters(
                question=question,
                analysis_type=analysis_type,
                semantic_resolution=semantic_resolution,
            ),
            dimensions=self._dimensions(semantic_resolution),
            confidence=self._confidence(
                analysis_type=analysis_type,
                metric=metric,
                business_entity=business_entity,
            ),
            warnings=warnings,
        )

    def _metrics(
        self,
        *,
        metric: str | None,
        semantic_resolution: SemanticResolution | None,
    ) -> list[str]:
        if semantic_resolution is not None and semantic_resolution.interpretation is not None:
            return semantic_resolution.interpretation.metrics

        return [metric] if metric is not None else []

    def _analysis_type(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution | None,
    ) -> str | None:
        if semantic_resolution is None:
            return None

        if (
            semantic_resolution.interpretation is not None
            and semantic_resolution.interpretation.intent is not None
        ):
            return semantic_resolution.interpretation.intent

        normalized_question = self._normalize_text(question)
        if self._is_comparison_question(normalized_question):
            return "comparison"

        if self._is_promocao_list_question(normalized_question, semantic_resolution):
            return "list_distinct"

        if any(term.canonical == "ranking" for term in semantic_resolution.matched_terms):
            return "ranking"

        return None

    def _is_comparison_question(self, normalized_question: str) -> bool:
        patterns = (
            r"\bcompare\b",
            r"\bcomparar\b",
            r"\bcomparativo\b",
            r"\bversus\b",
            r"\bvs\b",
            r"\bcontra\b",
            r"\bem relacao a\b",
        )
        return any(re.search(pattern, normalized_question) for pattern in patterns)

    def _is_promocao_list_question(
        self,
        normalized_question: str,
        semantic_resolution: SemanticResolution,
    ) -> bool:
        has_promocao = any(
            entity.name == "promocao"
            for entity in semantic_resolution.suggested_entities
        )
        if not has_promocao:
            return False

        patterns = (
            r"\bquais\s+(campanhas|promocoes)\b",
            r"\bliste\s+(as\s+)?(campanhas|promocoes)\b",
            r"\b(campanhas|promocoes)\s+ocorreram\b",
        )
        return any(re.search(pattern, normalized_question) for pattern in patterns)

    def _filters(
        self,
        *,
        question: str,
        analysis_type: str | None,
        semantic_resolution: SemanticResolution | None,
    ) -> list[dict[str, Any]]:
        if semantic_resolution is None:
            return []

        filters = [
            {"type": parameter.type, "value": parameter.value}
            for parameter in semantic_resolution.parameters
            if parameter.type in {"limit", "period", "comparison", "order"}
        ]

        if analysis_type == "ranking" and self._is_best_campaign_question(question):
            limit_filter = {"type": "limit", "value": 1}
            if not any(filter_item.get("type") == "limit" for filter_item in filters):
                filters.append(limit_filter)

        return filters

    def _metric(
        self,
        *,
        question: str,
        analysis_type: str | None,
        semantic_resolution: SemanticResolution | None,
    ) -> tuple[str | None, str | None]:
        if semantic_resolution is None:
            return None, None

        if (
            semantic_resolution.interpretation is not None
            and semantic_resolution.interpretation.metrics
        ):
            return semantic_resolution.interpretation.metrics[0], "semantic_dictionary"

        resolved_metric = self._metric_resolver.resolve(question)
        if resolved_metric.metric is not None:
            return resolved_metric.metric, resolved_metric.source

        if analysis_type == "ranking" and self._is_best_campaign_question(question):
            return "faturamento", "business_default"

        metric_names = {metric.name for metric in semantic_resolution.suggested_metrics}
        if "faturamento" in metric_names:
            return "faturamento", "explicit"

        if "ticket_medio" in metric_names:
            return "ticket_medio", "explicit"

        if "clientes_unicos" in metric_names:
            return "clientes_unicos", "explicit"

        if "quantidade_compras" in metric_names:
            return "quantidade_compras", "explicit"

        return None, None

    def _is_best_campaign_question(self, question: str) -> bool:
        normalized_question = self._normalize_text(question)
        return bool(
            re.search(r"\b(melhor|maior)\s+(campanha|promocao)\b", normalized_question)
            or re.search(r"\b(campanha|promocao)\s+(melhor|maior)\b", normalized_question)
        )

    def _business_entity(self, semantic_resolution: SemanticResolution | None) -> str | None:
        if semantic_resolution is None:
            return None

        if (
            semantic_resolution.interpretation is not None
            and semantic_resolution.interpretation.entity is not None
        ):
            return semantic_resolution.interpretation.entity

        entity_names = {entity.name for entity in semantic_resolution.suggested_entities}
        normalized_query = semantic_resolution.normalized_query
        if (
            "promocao" in entity_names
            or "campanha" in normalized_query
            or "campanhas" in normalized_query
            or "promocao" in normalized_query
            or "promocoes" in normalized_query
        ):
            return "promocao"

        if "restaurante" in entity_names:
            return "restaurante"

        if "loja" in entity_names:
            return "loja"

        return None

    def _dimensions(self, semantic_resolution: SemanticResolution | None) -> list[str]:
        if semantic_resolution is None or semantic_resolution.interpretation is None:
            return []

        return semantic_resolution.interpretation.dimensions

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

    def _normalize_text(self, text: str) -> str:
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFKD", text.lower())
            if not unicodedata.combining(char)
        )
        alphanumeric_text = re.sub(r"[^a-z0-9_]+", " ", without_accents)
        return re.sub(r"\s+", " ", alphanumeric_text).strip()

import re
import unicodedata

from app.context_resolution.models import (
    ResolvedContext,
    ResolvedDimension,
    ResolvedFilter,
    ResolvedMetric,
)
from app.entity_resolution.entity_resolver import EntityResolver
from app.knowledge.business_concepts import BUSINESS_CONCEPTS
from app.metrics.metric_resolver import MetricResolver


class ContextResolver:
    def __init__(
        self,
        *,
        entity_resolver: EntityResolver | None = None,
        metric_resolver: MetricResolver | None = None,
    ) -> None:
        self._entity_resolver = entity_resolver or EntityResolver()
        self._metric_resolver = metric_resolver or MetricResolver()

    def resolve(self, question: str) -> ResolvedContext:
        normalized = self._normalize_text(question)
        dimensions = self._dimensions(normalized)
        filters = self._filters(
            question=question,
            normalized_question=normalized,
            dimensions=dimensions,
        )
        intent = self._intent(normalized)
        metrics = self._metrics(question=question, normalized_question=normalized, intent=intent)
        warnings = self._warnings(dimensions)

        return ResolvedContext(
            filters=filters,
            dimensions=dimensions,
            metrics=metrics,
            intent=intent,
            warnings=warnings,
        )

    def _filters(
        self,
        *,
        question: str,
        normalized_question: str,
        dimensions: list[ResolvedDimension],
    ) -> list[ResolvedFilter]:
        filters: list[ResolvedFilter] = []
        entity_result = self._entity_resolver.resolve_many(question)
        for match in entity_result.matches:
            concept = self._concept_for_field(match.field)
            if concept is None:
                continue

            if not self._is_filter_context(concept, normalized_question):
                continue

            filters.append(
                ResolvedFilter(
                    concept=concept,
                    field=match.field,
                    operator="equals",
                    value=match.value,
                    label=match.value,
                    confidence=match.confidence,
                ),
            )

        filters.extend(self._explicit_dimension_value_filters(question))
        filters.extend(self._null_exclusion_filters(normalized_question, dimensions))
        return filters

    def _dimensions(self, normalized_question: str) -> list[ResolvedDimension]:
        patterns = (
            (
                "loja",
                r"\b(qual|quais)\s+(foi\s+a\s+|foi\s+o\s+)?lojas?\b"
                r"|\bloja\s+(mais|de\s+maior)\b",
            ),
            (
                "campanha",
                r"\b(qual|quais)\s+campanhas?\b|\bcampanha\s+mais\b|\bmelhor\s+campanha\b",
            ),
            (
                "segmento",
                r"\b(qual|quais)\s+(foi\s+o\s+)?segmentos?\b"
                r"|\bpor\s+segmento\b|\bsegmento\s+(mais|de\s+maior)\b",
            ),
            (
                "bairro",
                r"\b(qual|quais)\s+(foi\s+o\s+)?bairros?\b"
                r"|\bpor\s+bairro\b|\bbairro\s+(mais|de\s+maior)\b",
            ),
            (
                "cidade",
                r"\b(qual|quais)\s+(foi\s+a\s+)?cidades?\b"
                r"|\bpor\s+cidade\b|\bcidade\s+(mais|de\s+maior)\b",
            ),
            (
                "cliente",
                r"\b(qual|quais)\s+(foi\s+o\s+)?clientes?\b"
                r"|\bpor\s+cliente\b|\bcliente\s+(mais|de\s+maior)\b",
            ),
            ("empreendimento", r"\bpor\s+shopping\b|\bpor\s+empreendimento\b"),
        )
        dimensions: list[ResolvedDimension] = []
        for concept_name, pattern in patterns:
            if not re.search(pattern, normalized_question):
                continue
            if (
                concept_name == "cliente"
                and re.search(r"\bticket\s+medio\s+por\s+cliente\b", normalized_question)
            ):
                continue

            concept = BUSINESS_CONCEPTS[concept_name]
            dimensions.append(
                ResolvedDimension(
                    concept=concept_name,
                    field=concept.label_fields[0],
                    label=concept.entity_name,
                ),
            )

        return dimensions

    def _null_exclusion_filters(
        self,
        normalized_question: str,
        dimensions: list[ResolvedDimension],
    ) -> list[ResolvedFilter]:
        if not dimensions or not self._has_null_exclusion(normalized_question):
            return []

        return [
            ResolvedFilter(
                concept=dimension.concept,
                field=dimension.field,
                operator="not_null",
                value=None,
                label=None,
                confidence=1.0,
            )
            for dimension in dimensions
        ]

    def _explicit_dimension_value_filters(self, question: str) -> list[ResolvedFilter]:
        filters: list[ResolvedFilter] = []
        patterns = (
            ("segmento", r"\bsegmento\s+(.+?)(?=\s+(?:na|no|da|do|em)\b|$)"),
            ("bairro", r"\bbairro\s+(.+?)(?=\s+(?:na|no|da|do|em)\b|$)"),
            ("cidade", r"\bcidade\s+(.+?)(?=\s+(?:na|no|da|do|em)\b|$)"),
        )
        for concept_name, pattern in patterns:
            match = re.search(pattern, question, flags=re.IGNORECASE)
            if match is None:
                continue

            value = match.group(1).strip(" .?!,;:")
            if not value:
                continue
            if self._starts_with_filter_stopword(value):
                continue

            concept = BUSINESS_CONCEPTS[concept_name]
            filters.append(
                ResolvedFilter(
                    concept=concept_name,
                    field=concept.label_fields[0],
                    operator="equals",
                    value=value,
                    label=value,
                    confidence=1.0,
                ),
            )

        return filters

    def _starts_with_filter_stopword(self, value: str) -> bool:
        normalized = self._normalize_text(value)
        first_token = normalized.split(maxsplit=1)[0] if normalized else ""
        return first_token in {"com", "de", "da", "do", "que", "mais", "maior", "menor"}

    def _metrics(
        self,
        *,
        question: str,
        normalized_question: str,
        intent: str | None,
    ) -> list[ResolvedMetric]:
        metric = self._metric_resolver.resolve(question).metric
        if metric is None:
            if (
                "participacao" in normalized_question
                or "comprou" in normalized_question
                or "compraram" in normalized_question
            ):
                metric = "quantidade_compras"
            elif intent == "ranking":
                metric = "faturamento"

        if metric is None:
            return []

        return [self._metric(metric)]

    def _intent(self, normalized_question: str) -> str | None:
        if re.search(
            r"\b(detalhar|detalhe|detalha|resumo|como foi)\b.*\b(campanha|promocao)\b",
            normalized_question,
        ) or re.search(
            r"\b(campanha|promocao)\b.*\b(detalhar|detalhe|detalha|resumo|como foi)\b",
            normalized_question,
        ):
            return "campaign_detail"

        if re.search(r"\b(resumo|resuma|visao geral)\b", normalized_question):
            return "summary"

        ranking_pattern = r"\b(melhor|maior|mais vendeu|mais comprou|top|ranking)\b"
        if re.search(ranking_pattern, normalized_question):
            return "ranking"

        return None

    def _has_null_exclusion(self, normalized_question: str) -> bool:
        null_patterns = (
            r"\bexceto\s+null\b",
            r"\bignorando\s+nulos\b",
            r"\bdesconsiderando\s+nulos\b",
            r"\bsomente\s+preenchidos\b",
            r"\bsem\s+valores\s+vazios\b",
        )
        return any(re.search(pattern, normalized_question) for pattern in null_patterns)

    def _is_filter_context(self, concept: str, normalized_question: str) -> bool:
        if concept == "campanha":
            return bool(
                re.search(
                    r"\b(na|no|da|do|para a|para o)\s+campanha\b",
                    normalized_question,
                ),
            )

        if concept == "empreendimento":
            return bool(
                re.search(
                    r"\b(no|na|do|da|para o|para a)\s+(shopping|empreendimento)\b",
                    normalized_question,
                ),
            )

        if concept == "loja":
            return bool(re.search(r"\b(na|no|da|do)\s+loja\b", normalized_question))

        if concept == "bairro":
            return bool(re.search(r"\b(no|do)\s+bairro\b", normalized_question))

        return False

    def _concept_for_field(self, field: str) -> str | None:
        for concept_name, concept in BUSINESS_CONCEPTS.items():
            if field in concept.label_fields:
                return concept_name

        return None

    def _metric(self, name: str) -> ResolvedMetric:
        mapping = {
            "faturamento": ResolvedMetric(name="faturamento", aggregation="sum", field="vl_compra"),
            "quantidade_compras": ResolvedMetric(
                name="quantidade_compras",
                aggregation="count_distinct",
                field="cd_compra",
            ),
            "clientes_unicos": ResolvedMetric(
                name="clientes_unicos",
                aggregation="count_distinct",
                field="sk_cliente",
            ),
            "ticket_medio": ResolvedMetric(
                name="ticket_medio",
                formula="faturamento / quantidade_compras",
            ),
            "ticket_medio_por_compra": ResolvedMetric(
                name="ticket_medio_por_compra",
                formula="faturamento / quantidade_compras",
            ),
            "ticket_medio_por_cliente": ResolvedMetric(
                name="ticket_medio_por_cliente",
                formula="faturamento / clientes_unicos",
            ),
        }
        return mapping[name]

    def _warnings(self, dimensions: list[ResolvedDimension]) -> list[str]:
        if any(dimension.concept == "cidade" for dimension in dimensions):
            return ["Dimensão cidade depende da disponibilidade da coluna cidade no schema."]

        return []

    def _normalize_text(self, text: str) -> str:
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFKD", text.lower())
            if not unicodedata.combining(char)
        )
        alphanumeric_text = re.sub(r"[^a-z0-9_]+", " ", without_accents)
        return re.sub(r"\s+", " ", alphanumeric_text).strip()

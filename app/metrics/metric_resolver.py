import re
import unicodedata

from app.metrics.models import MetricResolutionResult


class MetricResolver:
    """Resolves explicit business metric mentions in user questions."""

    _MAPPINGS: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "quantidade_compras",
            (
                "volume de notas",
                "quantidade de notas",
                "qtd notas",
                "notas",
                "compras",
                "compras cadastradas",
            ),
        ),
        (
            "ticket_medio_por_cliente",
            (
                "ticket medio por cliente",
                "gasto medio por cliente",
            ),
        ),
        (
            "ticket_medio_por_compra",
            (
                "ticket medio por compra",
            ),
        ),
        (
            "ticket_medio",
            (
                "ticket medio",
                "ticket",
            ),
        ),
        (
            "clientes_unicos",
            (
                "clientes unicos",
                "clientes",
                "consumidores",
            ),
        ),
        (
            "faturamento",
            (
                "faturamento",
                "receita",
                "vendas",
            ),
        ),
    )

    def resolve(self, question: str) -> MetricResolutionResult:
        normalized_question = self._normalize_text(question)
        for metric, terms in self._MAPPINGS:
            for term in terms:
                if self._contains_term(normalized_question, term):
                    return MetricResolutionResult(
                        metric=metric,
                        source="explicit",
                        confidence=1.0,
                        matched_term=term,
                    )

        return MetricResolutionResult()

    def _contains_term(self, normalized_question: str, term: str) -> bool:
        pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
        return re.search(pattern, normalized_question) is not None

    def _normalize_text(self, text: str) -> str:
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFKD", text.lower())
            if not unicodedata.combining(char)
        )
        alphanumeric_text = re.sub(r"[^a-z0-9_]+", " ", without_accents)
        return re.sub(r"\s+", " ", alphanumeric_text).strip()

import re
import unicodedata

from app.intent_guard.models import IntentGuardResult

INSTITUTIONAL_OUT_OF_SCOPE_RESPONSE = (
    "Olá! Eu sou o Terbie, o Cientista de Dados da Terral.\n\n"
    "Meu propósito é ajudar na análise de dados e na geração de insights estratégicos "
    "para apoiar a tomada de decisão.\n\n"
    "Posso responder perguntas relacionadas a indicadores, vendas, clientes, campanhas, "
    "lojas, segmentos, empreendimentos, comportamento de consumo e outras análises de "
    "negócio.\n\n"
    "Para esse tipo de pergunta, infelizmente ela está fora do meu escopo de atuação."
)


class IntentGuard:
    """Deterministic guard that keeps non-BI questions out of the analytical pipeline."""

    _ANALYTICAL_TERMS = {
        "analise",
        "analisar",
        "campanha",
        "campanhas",
        "cliente",
        "clientes",
        "comparar",
        "compras",
        "consumo",
        "conversao",
        "desempenho",
        "empreendimento",
        "empreendimentos",
        "faturamento",
        "indicador",
        "indicadores",
        "loja",
        "lojas",
        "maior",
        "menor",
        "metricas",
        "promocao",
        "promocoes",
        "ranking",
        "receita",
        "restaurante",
        "restaurantes",
        "segmento",
        "segmentos",
        "ticket",
        "venda",
        "vendas",
        "vendeu",
    }
    _ANALYTICAL_PHRASES = (
        "ticket medio",
        "vendeu mais",
        "maior faturamento",
        "menor faturamento",
        "quantas vendas",
        "quanto vendeu",
        "total de vendas",
    )
    _NON_ANALYTICAL_PATTERNS = (
        r"^(ola|oi|opa|e ai|bom dia|boa tarde|boa noite|tudo bem)\??$",
        r"\bcomo voce trabalha\b",
        r"\bquem e voce\b",
        r"\bquem voce e\b",
        r"\bvoce me conhece\b",
        r"\bte conheco\b",
        r"\bconte uma piada\b",
        r"\bme conte uma piada\b",
        r"\bcomo esta o tempo\b",
        r"\bprevisao do tempo\b",
        r"\bqual seu nome\b",
        r"\bquem criou voce\b",
        r"\bquem te criou\b",
        r"\bo que voce faz\b",
        r"\bvoce e inteligente\b",
        r"\bme conte uma historia\b",
        r"\bconte uma historia\b",
    )

    def evaluate(self, question: str) -> IntentGuardResult:
        normalized_question = self._normalize_text(question)
        if normalized_question == "":
            return self._out_of_scope("empty_question", confidence=0.99)

        if self._has_analytical_intent(normalized_question):
            return IntentGuardResult(
                is_analytical=True,
                confidence=0.86,
                reason="business_analytical_terms_detected",
            )

        if self._matches_non_analytical_pattern(normalized_question):
            return self._out_of_scope("non_analytical_small_talk", confidence=0.96)

        return self._out_of_scope("no_business_analytical_intent_detected", confidence=0.74)

    def _has_analytical_intent(self, normalized_question: str) -> bool:
        if any(phrase in normalized_question for phrase in self._ANALYTICAL_PHRASES):
            return True

        tokens = set(normalized_question.split())
        return bool(tokens.intersection(self._ANALYTICAL_TERMS))

    def _matches_non_analytical_pattern(self, normalized_question: str) -> bool:
        return any(
            re.search(pattern, normalized_question)
            for pattern in self._NON_ANALYTICAL_PATTERNS
        )

    def _out_of_scope(self, reason: str, *, confidence: float) -> IntentGuardResult:
        return IntentGuardResult(
            is_analytical=False,
            confidence=confidence,
            reason=reason,
            response=INSTITUTIONAL_OUT_OF_SCOPE_RESPONSE,
        )

    def _normalize_text(self, text: str) -> str:
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFKD", text.lower())
            if not unicodedata.combining(char)
        )
        alphanumeric_text = re.sub(r"[^a-z0-9_]+", " ", without_accents)
        return re.sub(r"\s+", " ", alphanumeric_text).strip()

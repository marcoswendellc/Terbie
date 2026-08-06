import re
import unicodedata

from app.intent_guard.models import IntentGuardResult

INSTITUTIONAL_OUT_OF_SCOPE_RESPONSE = (
    "Eu posso ajudar com dados, indicadores e análises de negócio da Terral. "
    "Esse assunto está fora do meu escopo de atuação."
)
CAPABILITY_RESPONSE = (
    "Eu sou o Terbie, assistente de dados da Terral. Posso ajudar a consultar e analisar "
    "os dados disponíveis, incluindo "
    "indicadores, campanhas, lojas, clientes, segmentos e empreendimentos. Você pode "
    "pedir cálculos, comparações, rankings, filtros e resumos."
)
CLARIFICATION_RESPONSE = (
    "Pode especificar a campanha, empreendimento, período ou indicador ao qual você se refere?"
)


class IntentGuard:
    """Routes messages before semantic resolution and QueryPlan creation."""

    _ANALYTICAL_TERMS = {
        "analise",
        "analisar",
        "bairro",
        "campanha",
        "campanhas",
        "cliente",
        "clientes",
        "comparar",
        "compare",
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
        "nota",
        "notas",
        "promocao",
        "promocoes",
        "ranking",
        "receita",
        "resumo",
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
        "notas cadastradas",
        "quantidade de notas",
        "quantas vendas",
        "quantas notas",
        "quanto vendeu",
        "total de vendas",
    )
    _GREETING_PATTERNS = (
        r"^(ola|oi|opa|e ai|bom dia|boa tarde|boa noite|saudacoes|saudoso)( terbie)?$",
        r"^tudo bem( terbie)?$",
        r"^(obrigado|obrigada)( pela ajuda)?$",
        r"^(ate mais|ate logo|tchau)( terbie)?$",
    )
    _CAPABILITY_PATTERNS = (
        r"\bo que voce (faz|consegue fazer)\b",
        r"\bcomo voce pode me ajudar\b",
        r"\bcomo voce trabalha\b",
        r"\bque perguntas posso fazer\b",
        r"\bquem e voce\b",
        r"\bquem voce e\b",
        r"\bte conheco\b",
        r"\bvoce me conhece\b",
    )
    _DATA_CAPABILITY_PATTERNS = (
        (
            r"\bquais (dados|indicadores|campanhas|anos|periodos|lojas|segmentos|"
            r"empreendimentos) (existem|estao disponiveis|voce conhece)( na base)?\b"
        ),
        r"\bo que (existe|tem) na base\b",
        r"\b(disponivel|disponiveis) na base\b",
        r"\b(conhece|existem) na base\b",
    )
    _CLARIFICATION_PATTERNS = (
        r"^qual (foi )?o melhor$",
        r"^qual (foi )?a melhor$",
        r"^quanto vendeu$",
        r"^compare as campanhas$",
        r"^e no outro shopping$",
    )
    _EXPLICIT_OUT_OF_SCOPE_PATTERNS = (
        r"\bquem descobriu o brasil\b",
        r"\b(previsao do tempo|como esta o tempo|vai chover)\b",
        r"\b(conte|contar|me conte) (uma )?(piada|historia)\b",
        r"\b(resultado do jogo|placar do jogo)\b",
    )

    def evaluate(self, question: str) -> IntentGuardResult:
        normalized = self._normalize_text(question)
        if normalized == "":
            return self._clarification("empty_question", confidence=0.99)

        # Mandatory precedence: greeting -> capability -> data_query ->
        # clarification -> out_of_scope.
        if self._matches(normalized, self._GREETING_PATTERNS) or self._is_social_greeting(
            normalized,
        ):
            return IntentGuardResult(
                intent="greeting",
                requires_data=False,
                should_stop=True,
                confidence=0.99,
                reason="social_interaction_detected",
                response=self._greeting_response(normalized),
            )

        if self._matches(normalized, self._DATA_CAPABILITY_PATTERNS):
            return IntentGuardResult(
                intent="capability",
                requires_data=True,
                should_stop=False,
                confidence=0.94,
                reason="real_data_catalog_content_requested",
            )

        if self._matches(normalized, self._CAPABILITY_PATTERNS):
            return IntentGuardResult(
                intent="capability",
                requires_data=False,
                should_stop=True,
                confidence=0.97,
                reason="general_capability_question",
                response=CAPABILITY_RESPONSE,
            )

        # These forms are related to data, but still lack the entity, metric or
        # context needed to build a safe plan.
        if self._matches(normalized, self._CLARIFICATION_PATTERNS):
            return self._clarification("ambiguous_business_question", confidence=0.91)

        if self._has_analytical_intent(normalized):
            return IntentGuardResult(
                intent="data_query",
                requires_data=True,
                should_stop=False,
                confidence=0.86,
                reason="business_analytical_terms_detected",
            )

        if self._matches(normalized, self._EXPLICIT_OUT_OF_SCOPE_PATTERNS):
            return self._out_of_scope("explicit_non_business_intent", confidence=0.95)

        # Questions not covered by the vocabulary are allowed into semantic
        # reasoning. The compiler still validates every metric, dimension and
        # operation before data execution.
        return IntentGuardResult(
            intent="data_query",
            requires_data=True,
            should_stop=False,
            confidence=0.55,
            reason="open_semantic_reasoning_candidate",
        )

    def _has_analytical_intent(self, normalized: str) -> bool:
        if any(phrase in normalized for phrase in self._ANALYTICAL_PHRASES):
            return True
        return bool(set(normalized.split()).intersection(self._ANALYTICAL_TERMS))

    def _is_social_greeting(self, normalized: str) -> bool:
        starts_with_greeting = bool(
            re.match(
                r"^(ola|oi|opa|e ai|bom dia|boa tarde|boa noite|saudacoes|saudoso)\b",
                normalized,
            ),
        )
        asks_about_capabilities = self._matches(normalized, self._CAPABILITY_PATTERNS)
        return (
            starts_with_greeting
            and not self._has_analytical_intent(normalized)
            and not asks_about_capabilities
        )

    def _matches(self, normalized: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(pattern, normalized) for pattern in patterns)

    def _out_of_scope(self, reason: str, *, confidence: float) -> IntentGuardResult:
        return IntentGuardResult(
            intent="out_of_scope",
            requires_data=False,
            should_stop=True,
            confidence=confidence,
            reason=reason,
            response=INSTITUTIONAL_OUT_OF_SCOPE_RESPONSE,
        )

    def _clarification(self, reason: str, *, confidence: float) -> IntentGuardResult:
        return IntentGuardResult(
            intent="clarification",
            requires_data=False,
            should_stop=True,
            confidence=confidence,
            reason=reason,
            response=CLARIFICATION_RESPONSE,
        )

    def _greeting_response(self, normalized: str) -> str:
        if normalized.startswith(("obrigado", "obrigada")):
            return "Por nada! Conte comigo para ajudar com os dados."
        if normalized.startswith(("ate mais", "ate logo", "tchau")):
            return "Até mais! Quando precisar, estou por aqui."
        if normalized.startswith("tudo bem"):
            return "Tudo bem! Como posso ajudar você com os dados hoje?"
        if normalized.startswith("boa tarde"):
            return "Boa tarde! Como posso ajudar você com os dados hoje?"
        if normalized.startswith("boa noite"):
            return "Boa noite! Como posso ajudar você com os dados hoje?"
        if normalized.startswith("bom dia"):
            return "Bom dia! Como posso ajudar você com os dados hoje?"
        return "Olá! Como posso ajudar você com os dados hoje?"

    def _normalize_text(self, text: str) -> str:
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFKD", text.lower())
            if not unicodedata.combining(char)
        )
        alphanumeric_text = re.sub(r"[^a-z0-9_]+", " ", without_accents)
        return re.sub(r"\s+", " ", alphanumeric_text).strip()

from app.semantic_kb.models import KBContextRule

KB_CONTEXTS: list[KBContextRule] = [
    KBContextRule(
        id="promotion_question_context",
        description="Perguntas com campanha/promocao usam contexto promocional.",
        triggers=["campanha", "campanhas", "promocao", "promocoes", "acao promocional"],
        defaults={"entity": "promocao", "dimension": "nm_promocao"},
    ),
    KBContextRule(
        id="restaurant_question_context",
        description="Perguntas sobre restaurantes usam lojas do segmento alimentacao.",
        triggers=["restaurante", "restaurantes", "alimentacao"],
        defaults={"entity": "restaurante", "filter": {"field": "segmento", "value": "Alimentacao"}},
    ),
]


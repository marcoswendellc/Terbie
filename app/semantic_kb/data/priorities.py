from app.semantic_kb.models import KBPriorityRule

KB_PRIORITIES: list[KBPriorityRule] = [
    KBPriorityRule(
        id="promotion_terms_prefer_promotion_entity",
        description="Termos campanha/promocao/acao preferem a entidade promocao.",
        target="promocao",
        priority=10,
    ),
    KBPriorityRule(
        id="explicit_metric_over_business_default",
        description="Metricas explicitamente citadas vencem defaults de negocio.",
        target="metric_source:explicit",
        priority=5,
    ),
]


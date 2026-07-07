from app.semantic_kb import get_semantic_kb

SEMANTIC_BUSINESS_RULES: dict[str, dict[str, object]] = {
    rule.id: {
        "description": rule.description,
        "fields": rule.fields,
        "concepts": rule.concepts,
        "condition": rule.condition,
        "effect": rule.effect,
        "priority": rule.priority,
    }
    for rule in get_semantic_kb().knowledge_base.business_rules
}


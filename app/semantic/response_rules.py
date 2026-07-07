from app.semantic_kb import get_semantic_kb

SEMANTIC_RESPONSE_RULES: dict[str, dict[str, object]] = get_semantic_kb().response_rules()


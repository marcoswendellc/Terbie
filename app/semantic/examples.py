from app.semantic_kb import get_semantic_kb

SEMANTIC_EXAMPLES: list[dict[str, object]] = get_semantic_kb().examples()


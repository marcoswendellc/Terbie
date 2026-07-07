from app.semantic_kb import get_semantic_kb

SEMANTIC_DICTIONARY: dict[str, object] = get_semantic_kb().as_semantic_dictionary()


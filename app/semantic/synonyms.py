from typing import Any

from app.semantic.dictionary import SEMANTIC_DICTIONARY


def _synonyms(section: str) -> dict[str, list[str]]:
    items = SEMANTIC_DICTIONARY[section]
    if not isinstance(items, dict):
        return {}

    return {
        canonical: list(definition.get("synonyms", []))
        for canonical, definition in items.items()
        if isinstance(canonical, str) and isinstance(definition, dict)
    }


BUSINESS_SYNONYMS: dict[str, list[str]] = {
    **_synonyms("metrics"),
    **_synonyms("dimensions"),
    **_synonyms("intents"),
}

USER_TERM_COLUMN_MAP: dict[str, str | list[str]] = {
    term: column
    for term, column in SEMANTIC_DICTIONARY.get("column_mappings", {}).items()
    if isinstance(term, str) and isinstance(column, str | list)
}

SEMANTIC_SECTIONS: dict[str, dict[str, dict[str, Any]]] = {
    section: value
    for section, value in SEMANTIC_DICTIONARY.items()
    if section in {"metrics", "dimensions", "intents"} and isinstance(value, dict)
}

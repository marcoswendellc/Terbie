from app.semantic.dictionary import SEMANTIC_DICTIONARY
from app.semantic.models import SemanticEntity


def _build_entities() -> dict[str, SemanticEntity]:
    entities: dict[str, SemanticEntity] = {}
    entity_definitions = SEMANTIC_DICTIONARY["dimensions"]
    if not isinstance(entity_definitions, dict):
        return entities

    for name, definition in entity_definitions.items():
        if not isinstance(name, str) or not isinstance(definition, dict):
            continue

        entities[name] = SemanticEntity(
            name=name,
            column=definition.get("column"),
            key=definition.get("key"),
            date_fields=list(definition.get("date_fields", [])),
            synonyms=list(definition.get("synonyms", [])),
        )

    return entities


SEMANTIC_ENTITIES: dict[str, SemanticEntity] = _build_entities()

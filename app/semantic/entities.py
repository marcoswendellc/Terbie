from app.semantic.models import SemanticEntity
from app.semantic.synonyms import BUSINESS_SYNONYMS

SEMANTIC_ENTITIES: dict[str, SemanticEntity] = {
    "loja": SemanticEntity(name="loja", synonyms=BUSINESS_SYNONYMS["loja"]),
    "restaurante": SemanticEntity(
        name="restaurante",
        synonyms=BUSINESS_SYNONYMS["restaurante"],
    ),
    "cliente": SemanticEntity(name="cliente", synonyms=BUSINESS_SYNONYMS["cliente"]),
    "shopping": SemanticEntity(name="shopping", synonyms=BUSINESS_SYNONYMS["shopping"]),
    "categoria": SemanticEntity(
        name="categoria",
        synonyms=["categoria", "categorias", "segmento", "segmentos"],
    ),
    "data": SemanticEntity(name="data", synonyms=BUSINESS_SYNONYMS["data"]),
    "produto": SemanticEntity(
        name="produto",
        synonyms=["produto", "produtos", "item", "itens"],
    ),
    "promocao": SemanticEntity(
        name="promocao",
        synonyms=BUSINESS_SYNONYMS["promocao"],
    ),
}

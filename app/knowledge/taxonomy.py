from app.knowledge.models import BusinessTaxonomy

SEGMENT_TAXONOMY = BusinessTaxonomy(
    name="segmentos",
    source_field="nm_segmento",
    rules={
        "separator": ">>",
        "category_terms": {
            "restaurante": "Alimentação",
            "praça de alimentação": "Alimentação",
            "food": "Alimentação",
            "food court": "Alimentação",
        },
    },
)

BUSINESS_TAXONOMIES: list[BusinessTaxonomy] = [SEGMENT_TAXONOMY]


def parse_segment(segment: str) -> dict[str, str | None]:
    parts = [part.strip() for part in segment.split(">>", maxsplit=1)]
    category = parts[0] if parts and parts[0] else None
    subcategory = parts[1] if len(parts) > 1 and parts[1] else None
    return {"categoria": category, "subcategoria": subcategory}


def category_for_term(term: str) -> str | None:
    normalized_term = term.strip().lower()
    category_terms = SEGMENT_TAXONOMY.rules["category_terms"]
    return category_terms.get(normalized_term)

from app.semantic.examples import SEMANTIC_EXAMPLES
from app.semantic.resolver import SemanticResolver


def test_campaign_question_uses_semantic_dictionary_interpretation() -> None:
    resolution = SemanticResolver().resolve("Quais campanhas ocorreram em 2026?")

    assert resolution.interpretation is not None
    assert resolution.interpretation.intent == "list_distinct"
    assert resolution.interpretation.entity == "promocao"
    assert resolution.interpretation.operation == "distinct"
    assert resolution.interpretation.dimensions == ["nm_promocao"]
    assert {
        "type": "filter",
        "field": "sk_dtinicio",
        "operator": "year_overlap",
        "value": 2026,
        "end_field": "sk_dtfim",
        "source": "semantic_dictionary",
    } in resolution.interpretation.filters
    assert any(
        mapped.column == "nm_promocao" and mapped.canonical == "promocao"
        for mapped in resolution.mapped_columns
    )


def test_semantic_dictionary_examples_are_available() -> None:
    assert any(
        example["question"] == "Quais campanhas ocorreram em 2026?"
        and example["interpretation"]["dimension"] == "nm_promocao"
        for example in SEMANTIC_EXAMPLES
    )


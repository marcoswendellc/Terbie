from fastapi.testclient import TestClient

from app.main import app
from app.semantic.resolver import SemanticResolver


def test_faturamento_is_recognized_as_metric() -> None:
    resolution = SemanticResolver().resolve("Qual foi o faturamento deste mês?")

    assert any(
        term.canonical == "faturamento" and term.type == "metric"
        for term in resolution.matched_terms
    )
    assert [metric.name for metric in resolution.suggested_metrics] == ["faturamento"]


def test_restaurante_is_recognized_as_entity() -> None:
    resolution = SemanticResolver().resolve(
        "Quais são os 10 restaurantes com maior faturamento?",
    )

    assert any(
        term.canonical == "restaurante" and term.type == "entity"
        for term in resolution.matched_terms
    )
    assert any(entity.name == "restaurante" for entity in resolution.suggested_entities)


def test_vendas_is_recognized_as_faturamento() -> None:
    resolution = SemanticResolver().resolve("Quais lojas tiveram mais vendas?")

    assert any(
        term.term == "vendas" and term.canonical == "faturamento" and term.type == "metric"
        for term in resolution.matched_terms
    )


def test_ticket_medio_is_recognized() -> None:
    resolution = SemanticResolver().resolve("Qual o ticket médio por restaurante?")

    assert any(
        term.canonical == "ticket_medio" and term.type == "metric"
        for term in resolution.matched_terms
    )
    assert [metric.name for metric in resolution.suggested_metrics] == ["ticket_medio"]


def test_unknown_question_returns_empty_matches() -> None:
    resolution = SemanticResolver().resolve("Como está o clima hoje?")

    assert resolution.matched_terms == []
    assert resolution.suggested_metrics == []
    assert resolution.suggested_entities == []


def test_semantic_resolve_endpoint() -> None:
    client = TestClient(app)

    response = client.post(
        "/semantic/resolve",
        json={"question": "Quais restaurantes venderam mais este mês?"},
    )

    assert response.status_code == 200
    body = response.json()
    terms = body["resolution"]["matched_terms"]
    assert any(
        term["term"] == "restaurantes"
        and term["canonical"] == "restaurante"
        and term["type"] == "entity"
        and term["confidence"] == 1.0
        and term["source"] == "synonym"
        for term in terms
    )
    assert any(term["canonical"] == "faturamento" for term in terms)


def test_top_10_restaurantes_extracts_limit() -> None:
    resolution = SemanticResolver().resolve("Top 10 restaurantes")

    assert any(
        parameter.type == "limit" and parameter.value == 10
        for parameter in resolution.parameters
    )


def test_10_restaurantes_extracts_limit() -> None:
    resolution = SemanticResolver().resolve("Quais são os 10 restaurantes com maior faturamento?")

    assert any(
        parameter.type == "limit" and parameter.value == 10
        for parameter in resolution.parameters
    )


def test_ultimos_30_dias_extracts_period() -> None:
    resolution = SemanticResolver().resolve("Faturamento dos últimos 30 dias")

    assert any(
        parameter.type == "period" and parameter.value == "last_30_days"
        for parameter in resolution.parameters
    )


def test_este_mes_extracts_current_month_period() -> None:
    resolution = SemanticResolver().resolve("Vendas este mês")

    assert any(
        parameter.type == "period" and parameter.value == "current_month"
        for parameter in resolution.parameters
    )


def test_ano_passado_extracts_last_year_period() -> None:
    resolution = SemanticResolver().resolve("Faturamento ano passado")

    assert any(
        parameter.type == "period" and parameter.value == "last_year"
        for parameter in resolution.parameters
    )


def test_5_maiores_lojas_extracts_limit() -> None:
    resolution = SemanticResolver().resolve("5 maiores lojas")

    assert any(
        parameter.type == "limit" and parameter.value == 5
        for parameter in resolution.parameters
    )


def test_unknown_question_includes_warning_and_low_confidence() -> None:
    resolution = SemanticResolver().resolve("Como está o clima hoje?")

    assert resolution.warnings == ["Nenhuma métrica encontrada."]
    assert resolution.confidence == 0.0

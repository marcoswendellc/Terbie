from fastapi.testclient import TestClient

from app.main import app


def test_ask_draft_endpoint_returns_draft_created() -> None:
    client = TestClient(app)

    response = client.post(
        "/ask/draft",
        json={"question": "Quais são os 10 restaurantes com maior faturamento?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft_created"
    assert body["draft_plan"]["intent"] == "ranking"
    assert any(
        entity["name"] == "restaurante"
        for entity in body["draft_plan"]["entities"]
    )

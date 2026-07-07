from fastapi.testclient import TestClient

from app.main import app


def test_web_app_serves_login_shell() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Entrar no Terbie" in response.text
    assert "/ui/styles.css" in response.text
    assert "/ui/app.js" in response.text


def test_web_assets_are_served() -> None:
    client = TestClient(app)

    css_response = client.get("/ui/styles.css")
    js_response = client.get("/ui/app.js")

    assert css_response.status_code == 200
    assert js_response.status_code == 200

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


def test_chat_frontend_targets_backend_endpoints() -> None:
    client = TestClient(app)

    response = client.get("/ui/app.js")

    assert response.status_code == 200
    assert 'const EXECUTE_ENDPOINT = "/execute";' in response.text
    assert 'const DRAFT_ENDPOINT = "/ask/draft";' in response.text


def test_chat_frontend_does_not_render_raw_backend_warnings() -> None:
    client = TestClient(app)

    response = client.get("/ui/app.js")

    assert response.status_code == 200
    assert "payload.warnings" not in response.text
    assert "plan.warnings" not in response.text

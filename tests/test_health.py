from fastapi.testclient import TestClient

from main import app, get_allowed_origins

client = TestClient(app)


def test_health_returns_service_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "inventoryiq"
    assert body["version"] == app.version
    assert isinstance(body["ai_configured"], bool)


def test_health_reports_ai_configuration(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    assert client.get("/health").json()["ai_configured"] is True


def test_cors_allows_the_local_dev_origin() -> None:
    response = client.get("/", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_an_unknown_origin() -> None:
    response = client.get("/", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def test_allowed_origins_parses_a_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "https://inventoryiq.vercel.app, https://inventoryiq-git-main.vercel.app/",
    )

    assert get_allowed_origins() == [
        "https://inventoryiq.vercel.app",
        "https://inventoryiq-git-main.vercel.app",
    ]


def test_allowed_origins_falls_back_to_local_dev(monkeypatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "   ")

    assert get_allowed_origins() == ["http://localhost:5173"]

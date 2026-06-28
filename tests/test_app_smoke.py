from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint() -> None:
    class DummyContainer:
        pass

    client = TestClient(create_app(container=DummyContainer()))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

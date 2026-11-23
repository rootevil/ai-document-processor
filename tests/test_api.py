
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/api/v1/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to Document AI!",
        "status": "running",
    }


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
    }

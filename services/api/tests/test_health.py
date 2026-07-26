from fastapi.testclient import TestClient


def test_health_returns_service_identity_and_correlation_id(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Correlation-ID": "test-request"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}
    assert response.headers["x-correlation-id"] == "test-request"

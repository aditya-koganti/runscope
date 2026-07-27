import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from runscope_api.api import health as health_api
from runscope_api.api.health import DependencyStatus
from runscope_api.db import SessionFactory
from runscope_api.main import create_app
from runscope_api.models import Role, User
from runscope_api.security import create_access_token, hash_password


def test_health_returns_service_identity_and_correlation_id(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Correlation-ID": "test-request"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}
    assert response.headers["x-correlation-id"] == "test-request"


async def seed_viewer() -> str:
    async with SessionFactory() as session:
        viewer = User(
            email=f"health-viewer-{uuid4()}@runscope.dev",
            password_hash=hash_password("ViewerDemo123!"),
            role=Role.VIEWER,
        )
        session.add(viewer)
        await session.commit()
        return create_access_token(viewer)[0]


def test_platform_summary_dependencies_and_prometheus_metrics(
    client: TestClient,
    monkeypatch,
) -> None:
    async def healthy_dependencies(_settings):
        return {
            name: DependencyStatus(status="healthy", latency_ms=1.0)
            for name in ("api", "postgresql", "redis", "redpanda", "minio", "scheduler")
        }

    monkeypatch.setattr(health_api, "dependency_statuses", healthy_dependencies)
    token = asyncio.run(seed_viewer())
    headers = {"Authorization": f"Bearer {token}"}

    dependencies = client.get("/api/v1/platform/dependencies", headers=headers)
    assert dependencies.status_code == 200
    assert dependencies.json()["status"] == "healthy"
    assert set(dependencies.json()["dependencies"]) == {
        "api",
        "postgresql",
        "redis",
        "redpanda",
        "minio",
        "scheduler",
    }

    summary = client.get("/api/v1/platform/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["queue_depth"] == 0
    assert summary.json()["success_rate"] == 0

    metrics = client.get("/api/v1/metrics")
    assert metrics.status_code == 200
    assert "runscope_queue_depth" in metrics.text
    assert "runscope_http_requests_total" in metrics.text

    client.get(f"/api/v1/not-a-real-resource/{uuid4()}")
    metrics = client.get("/api/v1/metrics")
    assert 'path="unmatched"' in metrics.text


def test_readiness_returns_503_when_a_required_dependency_is_unavailable(
    client: TestClient,
    monkeypatch,
) -> None:
    async def degraded_dependencies(_settings):
        return {
            name: DependencyStatus(
                status="unavailable" if name == "redis" else "healthy",
                latency_ms=1.0,
            )
            for name in ("api", "postgresql", "redis", "redpanda", "minio", "scheduler")
        }

    monkeypatch.setattr(health_api, "dependency_statuses", degraded_dependencies)
    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["dependencies"]["redis"] == "unavailable"


def test_unexpected_errors_return_a_stable_body_and_correlation_id() -> None:
    app = create_app()

    @app.get("/api/v1/test-unexpected-error")
    async def raise_unexpected_error() -> None:
        raise RuntimeError("internal database detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/test-unexpected-error",
            headers={"X-Correlation-ID": "unexpected-test"},
        )

    assert response.status_code == 500
    assert response.headers["x-correlation-id"] == "unexpected-test"
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "An unexpected internal error occurred",
            "details": {},
            "correlation_id": "unexpected-test",
        }
    }
    assert "internal database detail" not in response.text

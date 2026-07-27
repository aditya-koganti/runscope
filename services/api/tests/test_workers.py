import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from runscope_api.db import SessionFactory
from runscope_api.models import Role, User
from runscope_api.security import create_access_token, hash_password


async def seed_users() -> tuple[str, str]:
    async with SessionFactory() as session:
        admin = User(
            email=f"worker-admin-{uuid4()}@runscope.dev",
            password_hash=hash_password("AdminDemo123!"),
            role=Role.ADMINISTRATOR,
        )
        viewer = User(
            email=f"worker-viewer-{uuid4()}@runscope.dev",
            password_hash=hash_password("ViewerDemo123!"),
            role=Role.VIEWER,
        )
        session.add_all([admin, viewer])
        await session.commit()
        return create_access_token(admin)[0], create_access_token(viewer)[0]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_worker_registration_heartbeat_and_reads(client: TestClient) -> None:
    admin_token, viewer_token = asyncio.run(seed_users())
    denied = client.post(
        "/api/v1/workers/register",
        headers=headers(viewer_token),
        json={"name": "api-worker", "total_cpu": 4, "total_memory_mb": 8192},
    )
    assert denied.status_code == 403

    registered = client.post(
        "/api/v1/workers/register",
        headers=headers(admin_token),
        json={"name": "api-worker", "total_cpu": 4, "total_memory_mb": 8192},
    )
    assert registered.status_code == 200, registered.text
    worker = registered.json()
    assert worker["status"] == "ONLINE"
    assert worker["available_cpu"] == 4

    listing = client.get("/api/v1/workers", headers=headers(viewer_token))
    assert listing.status_code == 200
    assert [item["name"] for item in listing.json()] == ["api-worker"]

    detail = client.get(
        f"/api/v1/workers/{worker['id']}",
        headers=headers(viewer_token),
    )
    assert detail.status_code == 200
    assert detail.json()["active_allocations"] == []

    heartbeat = client.post(
        f"/api/v1/workers/{worker['id']}/heartbeat",
        headers=headers(admin_token),
    )
    assert heartbeat.status_code == 200

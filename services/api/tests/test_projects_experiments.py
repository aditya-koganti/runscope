from fastapi.testclient import TestClient
from runscope_api.db import SessionFactory
from runscope_api.models import Role, User
from runscope_api.security import hash_password


async def create_user(email: str, password: str, role: Role) -> User:
    async with SessionFactory() as session:
        user = User(email=email, password_hash=hash_password(password), role=role)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def auth_headers(client: TestClient, role: Role) -> dict[str, str]:
    email = f"{role.value}@example.com"
    password = "ValidPassword123!"
    await create_user(email, password, role)
    response = client.post(
        "/api/v1/auth/sign-in",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_project_crud_search_sort_and_pagination(client: TestClient) -> None:
    headers = await auth_headers(client, Role.RESEARCHER)
    for name in ("Bravo", "Alpha", "Charlie"):
        response = client.post(
            "/api/v1/projects",
            headers=headers,
            json={"name": name, "description": f"{name} machine learning work"},
        )
        assert response.status_code == 201

    page = client.get(
        "/api/v1/projects?page=1&page_size=2&sort=name&direction=asc",
        headers=headers,
    )
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert page.json()["pages"] == 2
    assert [item["name"] for item in page.json()["items"]] == ["Alpha", "Bravo"]

    search = client.get("/api/v1/projects?search=charlie", headers=headers)
    project = search.json()["items"][0]
    assert search.json()["total"] == 1

    updated = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
        json={"description": "Updated description"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated description"

    read = client.get(f"/api/v1/projects/{project['id']}", headers=headers)
    assert read.status_code == 200
    assert read.json()["name"] == "Charlie"

    deleted = client.delete(f"/api/v1/projects/{project['id']}", headers=headers)
    assert deleted.status_code == 204
    missing = client.get(f"/api/v1/projects/{project['id']}", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "project_not_found"


async def test_viewer_can_read_but_cannot_create(client: TestClient) -> None:
    viewer_headers = await auth_headers(client, Role.VIEWER)

    listed = client.get("/api/v1/projects", headers=viewer_headers)
    denied = client.post(
        "/api/v1/projects",
        headers=viewer_headers,
        json={"name": "Forbidden project", "description": ""},
    )

    assert listed.status_code == 200
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "permission_denied"


async def test_experiment_crud_uniqueness_and_delete_conflict(client: TestClient) -> None:
    headers = await auth_headers(client, Role.RESEARCHER)
    project_response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Vision", "description": "Image experiments"},
    )
    project_id = project_response.json()["id"]

    created = client.post(
        "/api/v1/experiments",
        headers=headers,
        json={
            "project_id": project_id,
            "name": "Baseline",
            "description": "First controlled run",
            "tags": [" Baseline ", "IRIS", "iris"],
        },
    )
    assert created.status_code == 201
    experiment = created.json()
    assert experiment["tags"] == ["baseline", "iris"]

    duplicate = client.post(
        "/api/v1/experiments",
        headers=headers,
        json={
            "project_id": project_id,
            "name": "baseline",
            "description": "",
            "tags": [],
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "experiment_name_conflict"

    listed = client.get(
        f"/api/v1/experiments?project_id={project_id}&search=controlled&tag=iris",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    updated = client.patch(
        f"/api/v1/experiments/{experiment['id']}",
        headers=headers,
        json={"name": "Baseline v2", "tags": ["validated"]},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Baseline v2"

    project_conflict = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert project_conflict.status_code == 409
    assert project_conflict.json()["error"]["code"] == "project_has_experiments"

    assert (
        client.delete(
            f"/api/v1/experiments/{experiment['id']}",
            headers=headers,
        ).status_code
        == 204
    )
    assert client.delete(f"/api/v1/projects/{project_id}", headers=headers).status_code == 204

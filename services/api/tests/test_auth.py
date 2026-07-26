from fastapi.testclient import TestClient
from runscope_api.db import SessionFactory
from runscope_api.errors import AppError
from runscope_api.models import Role, User
from runscope_api.security import hash_password, require_roles, verify_password


async def create_user(email: str, password: str, role: Role) -> User:
    async with SessionFactory() as session:
        user = User(email=email, password_hash=hash_password(password), role=role)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def test_password_hash_is_not_plaintext() -> None:
    password_hash = hash_password("CorrectHorseBatteryStaple!")

    assert password_hash != "CorrectHorseBatteryStaple!"
    assert verify_password("CorrectHorseBatteryStaple!", password_hash)
    assert not verify_password("wrong-password", password_hash)


async def test_sign_in_and_current_user(client: TestClient) -> None:
    await create_user("researcher@example.com", "Researcher123!", Role.RESEARCHER)

    sign_in = client.post(
        "/api/v1/auth/sign-in",
        json={"email": "RESEARCHER@example.com", "password": "Researcher123!"},
    )

    assert sign_in.status_code == 200
    payload = sign_in.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["role"] == "researcher"

    current = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert current.status_code == 200
    assert current.json()["email"] == "researcher@example.com"


async def test_invalid_credentials_are_structured(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/sign-in",
        json={"email": "missing@example.com", "password": "WrongPassword123!"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert response.json()["error"]["correlation_id"]


async def test_current_user_requires_valid_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


async def test_viewer_is_denied_researcher_dependency() -> None:
    viewer = User(
        email="viewer@example.test",
        password_hash="not-used",
        role=Role.VIEWER,
    )
    dependency = require_roles(Role.RESEARCHER, Role.ADMINISTRATOR)

    try:
        await dependency(viewer)
    except AppError as exc:
        assert exc.status_code == 403
        assert exc.code == "permission_denied"
    else:
        raise AssertionError("Viewer should not satisfy researcher authorization")

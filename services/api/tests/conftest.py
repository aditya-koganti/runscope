import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("RUNSCOPE_DATABASE_URL", "sqlite+aiosqlite://")

from runscope_api.main import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client

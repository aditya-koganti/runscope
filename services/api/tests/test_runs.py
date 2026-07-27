from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from runscope_api.db import SessionFactory
from runscope_api.main import create_app
from runscope_api.models import Experiment, OutboxMessage, Project, Role, User
from runscope_api.security import create_access_token, hash_password
from runscope_api.seed import seed_training_templates
from runscope_api.storage import LocalArtifactStore, get_artifact_store
from runscope_contracts import EventEnvelope, LiveEvent
from runscope_worker.main import process_event
from sqlalchemy import select


class FailingLiveBus:
    async def publish(self, run_id: UUID, event_type: str, payload: dict[str, Any]) -> LiveEvent:
        raise ConnectionError("Redis unavailable in controlled test")

    async def subscribe(self, run_id: UUID) -> AsyncIterator[LiveEvent]:
        del run_id
        if False:
            yield


async def seed_run_context() -> tuple[User, Experiment]:
    async with SessionFactory() as session:
        user = User(
            email=f"researcher-{uuid4()}@runscope.dev",
            password_hash=hash_password("ResearcherDemo123!"),
            role=Role.RESEARCHER,
        )
        session.add(user)
        await session.flush()
        project = Project(
            name="Classification",
            description="",
            created_by=user.id,
        )
        session.add(project)
        await session.flush()
        experiment = Experiment(
            project_id=project.id,
            name="Iris baseline",
            description="",
            tags=["iris"],
            created_by=user.id,
        )
        session.add(experiment)
        await session.commit()
        await seed_training_templates(session)
        return user, experiment


def test_create_run_executes_template_and_exposes_outputs(
    tmp_path: Path,
) -> None:
    import asyncio

    user, experiment = asyncio.run(seed_run_context())
    token, _ = create_access_token(user)
    headers = {"Authorization": f"Bearer {token}"}
    app = create_app()
    store = LocalArtifactStore(tmp_path)

    async def store_override():
        yield store

    app.dependency_overrides[get_artifact_store] = store_override
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/runs",
            headers=headers,
            json={
                "experiment_id": str(experiment.id),
                "template_key": "sklearn-iris-classification",
                "parameters": {
                    "n_estimators": 20,
                    "max_depth": 4,
                    "test_size": 0.2,
                    "random_state": 7,
                },
                "requested_cpu": 1,
                "requested_memory_mb": 512,
            },
        )
        assert response.status_code == 201, response.text
        run = response.json()
        assert run["status"] == "QUEUED"
        run_id = run["id"]

        async def execute_from_outbox() -> None:
            async with SessionFactory() as session:
                outbox = await session.scalar(select(OutboxMessage))
                assert outbox is not None
                event = EventEnvelope.model_validate(outbox.envelope)
            assert await process_event(event, store, FailingLiveBus())
            assert not await process_event(event, store)

        asyncio.run(execute_from_outbox())
        completed = client.get(f"/api/v1/runs/{run_id}", headers=headers).json()
        assert completed["status"] == "SUCCEEDED"
        metrics = client.get(f"/api/v1/runs/{run_id}/metrics", headers=headers).json()
        logs = client.get(f"/api/v1/runs/{run_id}/logs", headers=headers).json()
        events = client.get(f"/api/v1/runs/{run_id}/events", headers=headers).json()
        artifacts = client.get(f"/api/v1/runs/{run_id}/artifacts", headers=headers).json()

        assert {metric["name"] for metric in metrics} == {
            "accuracy",
            "precision",
            "recall",
            "f1",
        }
        assert len(logs) == 3
        assert [event["new_status"] for event in events] == [
            "QUEUED",
            "SCHEDULING",
            "RUNNING",
            "SUCCEEDED",
        ]
        assert {artifact["name"] for artifact in artifacts} == {
            "model.joblib",
            "metrics.json",
            "metrics-chart.svg",
        }
        download = client.get(
            f"/api/v1/runs/{run_id}/artifacts/{artifacts[0]['id']}/download",
            headers=headers,
        )
        assert download.status_code == 200
        assert download.content

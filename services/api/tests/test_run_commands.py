import asyncio
from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from runscope_api.db import SessionFactory
from runscope_api.models import (
    Experiment,
    OutboxMessage,
    Project,
    Role,
    Run,
    RunMetric,
    RunParameter,
    RunStatus,
    TrainingTemplate,
    User,
)
from runscope_api.security import create_access_token, hash_password
from runscope_api.seed import seed_training_templates
from sqlalchemy import func, select


@dataclass(frozen=True)
class CommandContext:
    researcher_token: str
    viewer_token: str
    running_id: UUID
    failed_id: UUID
    successful_ids: tuple[UUID, UUID]


async def seed_command_context() -> CommandContext:
    async with SessionFactory() as session:
        researcher = User(
            email=f"command-researcher-{uuid4()}@runscope.dev",
            password_hash=hash_password("ResearcherDemo123!"),
            role=Role.RESEARCHER,
        )
        viewer = User(
            email=f"command-viewer-{uuid4()}@runscope.dev",
            password_hash=hash_password("ViewerDemo123!"),
            role=Role.VIEWER,
        )
        session.add_all([researcher, viewer])
        await session.flush()
        project = Project(name="Command tests", description="", created_by=researcher.id)
        session.add(project)
        await session.flush()
        experiment = Experiment(
            project_id=project.id,
            name="Lifecycle commands",
            description="",
            tags=[],
            created_by=researcher.id,
        )
        session.add(experiment)
        await session.commit()
        await seed_training_templates(session)
        slow_template = await session.scalar(
            select(TrainingTemplate).where(TrainingTemplate.key == "slow-demonstration")
        )
        classification_template = await session.scalar(
            select(TrainingTemplate).where(TrainingTemplate.key == "sklearn-iris-classification")
        )
        assert slow_template is not None
        assert classification_template is not None

        running = Run(
            experiment_id=experiment.id,
            template_id=slow_template.id,
            status=RunStatus.RUNNING,
            requested_cpu=1,
            requested_memory_mb=512,
            created_by=researcher.id,
        )
        failed = Run(
            experiment_id=experiment.id,
            template_id=slow_template.id,
            status=RunStatus.FAILED,
            requested_cpu=1,
            requested_memory_mb=512,
            failure_code="intentional_demo_failure",
            failure_message="Configured failure",
            created_by=researcher.id,
        )
        successful = [
            Run(
                experiment_id=experiment.id,
                template_id=classification_template.id,
                status=RunStatus.SUCCEEDED,
                requested_cpu=1,
                requested_memory_mb=512,
                created_by=researcher.id,
            )
            for _ in range(2)
        ]
        session.add_all([running, failed, *successful])
        await session.flush()
        session.add_all(
            [
                RunParameter(
                    run_id=failed.id,
                    name="duration_seconds",
                    value=2,
                ),
                RunParameter(
                    run_id=failed.id,
                    name="interval_seconds",
                    value=0.25,
                ),
                RunParameter(
                    run_id=failed.id,
                    name="fail_intentionally",
                    value=True,
                ),
                RunParameter(run_id=successful[0].id, name="n_estimators", value=20),
                RunParameter(run_id=successful[1].id, name="n_estimators", value=40),
                RunMetric(run_id=successful[0].id, name="accuracy", value=0.8, step=1),
                RunMetric(run_id=successful[1].id, name="accuracy", value=0.9, step=1),
                RunMetric(run_id=successful[0].id, name="f1", value=0.79, step=1),
                RunMetric(run_id=successful[1].id, name="f1", value=0.88, step=1),
            ]
        )
        await session.commit()
        researcher_token, _ = create_access_token(researcher)
        viewer_token, _ = create_access_token(viewer)
        return CommandContext(
            researcher_token=researcher_token,
            viewer_token=viewer_token,
            running_id=running.id,
            failed_id=failed.id,
            successful_ids=(successful[0].id, successful[1].id),
        )


def authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_cancel_retry_metadata_and_comparison_commands(client: TestClient) -> None:
    context = asyncio.run(seed_command_context())

    viewer_cancel = client.post(
        f"/api/v1/runs/{context.running_id}/cancel",
        headers=authorization(context.viewer_token),
    )
    assert viewer_cancel.status_code == 403

    cancelled = client.post(
        f"/api/v1/runs/{context.running_id}/cancel",
        headers=authorization(context.researcher_token),
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLING"

    retried = client.post(
        f"/api/v1/runs/{context.failed_id}/retry",
        headers=authorization(context.researcher_token),
        json={"parameter_overrides": {"fail_intentionally": False}},
    )
    assert retried.status_code == 201, retried.text
    child = retried.json()
    assert child["status"] == "QUEUED"
    assert child["parent_run_id"] == str(context.failed_id)
    assert child["attempt_number"] == 2
    child_parameters = client.get(
        f"/api/v1/runs/{child['id']}/parameters",
        headers=authorization(context.researcher_token),
    ).json()
    assert {item["name"]: item["value"] for item in child_parameters}["fail_intentionally"] is False

    metadata = client.patch(
        f"/api/v1/runs/{child['id']}/metadata",
        headers=authorization(context.researcher_token),
        json={"notes": "Reviewed retry", "tags": [" Baseline ", "baseline", "Safe"]},
    )
    assert metadata.status_code == 200, metadata.text
    assert metadata.json()["notes"] == "Reviewed retry"
    assert metadata.json()["tags"] == ["baseline", "safe"]

    comparison = client.post(
        "/api/v1/runs/compare",
        headers=authorization(context.viewer_token),
        json={"run_ids": [str(run_id) for run_id in context.successful_ids]},
    )
    assert comparison.status_code == 200, comparison.text
    payload = comparison.json()
    assert len(payload["items"]) == 2
    assert payload["items"][0]["parameters"]["n_estimators"] == 20
    assert payload["best_by_metric"] == {
        "accuracy": str(context.successful_ids[1]),
        "f1": str(context.successful_ids[1]),
    }

    duplicate_comparison = client.post(
        "/api/v1/runs/compare",
        headers=authorization(context.viewer_token),
        json={"run_ids": [str(context.successful_ids[0])] * 2},
    )
    assert duplicate_comparison.status_code == 422

    async def count_retry_events() -> int:
        async with SessionFactory() as session:
            return (
                await session.scalar(
                    select(func.count(OutboxMessage.id)).where(
                        OutboxMessage.envelope["event_type"].as_string() == "run.submitted"
                    )
                )
                or 0
            )

    assert asyncio.run(count_retry_events()) == 1

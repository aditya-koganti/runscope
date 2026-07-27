import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError
from runscope_contracts import EventEnvelope
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runscope_api.config import get_settings
from runscope_api.errors import AppError
from runscope_api.middleware import correlation_id_context
from runscope_api.models import (
    Artifact,
    OutboxMessage,
    Run,
    RunLog,
    RunMetric,
    RunParameter,
    RunStatus,
    TrainingTemplate,
)
from runscope_api.schemas.runs import RunCreate
from runscope_api.state_machine import transition_run
from runscope_api.storage import ArtifactStore
from runscope_api.templates.registry import registry

logger = logging.getLogger(__name__)


async def find_template(session: AsyncSession, key: str, version: str) -> TrainingTemplate:
    template = await session.scalar(
        select(TrainingTemplate).where(
            TrainingTemplate.key == key,
            TrainingTemplate.version == version,
            TrainingTemplate.enabled.is_(True),
        )
    )
    if template is None:
        raise AppError(
            "template_not_found",
            "The requested training template or version is not available",
            404,
        )
    try:
        registry.get(template.key, template.version)
    except KeyError as exc:
        raise AppError(
            "template_unregistered",
            "The template metadata is not backed by trusted executable code",
            409,
        ) from exc
    return template


def validate_parameters(
    template: TrainingTemplate, values: dict[str, Any]
) -> tuple[Any, dict[str, Any]]:
    definition = registry.get(template.key, template.version)
    try:
        validated = definition.validate_parameters(values)
    except ValidationError as exc:
        raise AppError(
            "invalid_template_parameters",
            "One or more template parameters are invalid",
            422,
            {"validation_errors": exc.errors(include_url=False)},
        ) from exc
    return validated, validated.model_dump(mode="json")


async def create_queued_run(
    session: AsyncSession,
    body: RunCreate,
    created_by: UUID,
) -> Run:
    template = await find_template(session, body.template_key, body.template_version)
    _, parameters = validate_parameters(template, body.parameters)
    run = Run(
        experiment_id=body.experiment_id,
        template_id=template.id,
        status=RunStatus.DRAFT,
        priority=body.priority,
        requested_cpu=body.requested_cpu,
        requested_memory_mb=body.requested_memory_mb,
        created_by=created_by,
        notes=body.notes,
        tags=list(dict.fromkeys(tag.strip().lower() for tag in body.tags if tag.strip())),
    )
    session.add(run)
    await session.flush()
    session.add_all(
        RunParameter(run_id=run.id, name=name, value=value) for name, value in parameters.items()
    )
    transition_run(session, run, RunStatus.QUEUED, "run.queued")
    event = EventEnvelope(
        event_id=uuid4(),
        event_type="run.submitted",
        occurred_at=datetime.now(UTC),
        correlation_id=correlation_id_context.get(),
        run_id=run.id,
        payload={
            "template_key": template.key,
            "template_version": template.version,
            "requested_cpu": run.requested_cpu,
            "requested_memory_mb": run.requested_memory_mb,
            "priority": run.priority,
        },
    )
    session.add(
        OutboxMessage(
            topic=get_settings().broker_topic,
            partition_key=str(run.id),
            envelope=event.model_dump(mode="json"),
        )
    )
    await session.commit()
    await session.refresh(run)
    return run


async def execute_existing_run(
    session: AsyncSession,
    artifact_store: ArtifactStore,
    run_id: UUID,
) -> Run | None:
    run = await session.get(Run, run_id)
    if run is None or run.status != RunStatus.QUEUED:
        return run
    template = await session.get(TrainingTemplate, run.template_id)
    if template is None:
        raise RuntimeError("Run references a missing training template")
    parameters = {
        parameter.name: parameter.value
        for parameter in (
            await session.scalars(select(RunParameter).where(RunParameter.run_id == run.id))
        ).all()
    }
    validated, _ = validate_parameters(template, parameters)
    transition_run(
        session,
        run,
        RunStatus.SCHEDULING,
        "run.scheduling",
        {"execution_mode": "background-worker"},
    )
    transition_run(session, run, RunStatus.RUNNING, "run.started")
    await session.commit()

    definition = registry.get(template.key, template.version)
    try:
        result = await asyncio.to_thread(definition.execute, validated)
        session.add_all(
            RunLog(
                run_id=run.id,
                sequence_number=sequence,
                level=level,
                message=message,
            )
            for sequence, (level, message) in enumerate(result.logs, start=1)
        )
        session.add_all(
            RunMetric(run_id=run.id, name=name, value=value, step=1)
            for name, value in result.metrics.items()
        )
        for generated in result.artifacts:
            storage_key = f"{run.id}/{generated.name}"
            await artifact_store.put(storage_key, generated.data, generated.mime_type)
            session.add(
                Artifact(
                    run_id=run.id,
                    name=generated.name,
                    storage_key=storage_key,
                    mime_type=generated.mime_type,
                    size_bytes=len(generated.data),
                    checksum=hashlib.sha256(generated.data).hexdigest(),
                )
            )
        transition_run(
            session,
            run,
            RunStatus.SUCCEEDED,
            "run.succeeded",
            {"metric_count": len(result.metrics), "artifact_count": len(result.artifacts)},
        )
        await session.commit()
    except Exception:
        logger.exception(
            "Trusted training-template execution failed", extra={"run_id": str(run.id)}
        )
        await session.rollback()
        failed_run = await session.get(Run, run.id)
        if failed_run is None:
            raise
        failed_run.failure_code = "template_execution_failed"
        failed_run.failure_message = "Trusted template execution failed"
        transition_run(session, failed_run, RunStatus.FAILED, "run.failed")
        await session.commit()
        run = failed_run
    await session.refresh(run)
    return run

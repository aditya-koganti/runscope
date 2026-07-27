from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from runscope_api.errors import AppError
from runscope_api.models import Run, RunEvent, RunStatus

VALID_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.DRAFT: frozenset({RunStatus.QUEUED}),
    RunStatus.QUEUED: frozenset({RunStatus.SCHEDULING}),
    RunStatus.SCHEDULING: frozenset({RunStatus.RUNNING, RunStatus.QUEUED}),
    RunStatus.RUNNING: frozenset({RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLING}),
    RunStatus.CANCELLING: frozenset({RunStatus.CANCELLED}),
    RunStatus.FAILED: frozenset({RunStatus.RETRYING}),
    RunStatus.RETRYING: frozenset({RunStatus.QUEUED}),
    RunStatus.SUCCEEDED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
}

TERMINAL_STATUSES = frozenset({RunStatus.SUCCEEDED, RunStatus.CANCELLED})


def validate_transition(previous: RunStatus, target: RunStatus) -> None:
    if target not in VALID_TRANSITIONS[previous]:
        raise AppError(
            "run_invalid_transition",
            f"Run cannot transition from {previous.value} to {target.value}",
            409,
            {"previous_status": previous.value, "requested_status": target.value},
        )


def transition_run(
    session: AsyncSession,
    run: Run,
    target: RunStatus,
    event_type: str,
    metadata: dict[str, Any] | None = None,
) -> RunEvent:
    previous = run.status
    validate_transition(previous, target)
    now = datetime.now(UTC)
    run.status = target
    if target == RunStatus.QUEUED and run.queued_at is None:
        run.queued_at = now
    if target == RunStatus.RUNNING:
        run.started_at = now
    if target in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}:
        run.completed_at = now
    event = RunEvent(
        run_id=run.id,
        event_type=event_type,
        previous_status=previous,
        new_status=target,
        event_metadata=metadata or {},
    )
    session.add(event)
    return event

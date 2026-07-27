"""create training templates and runs

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None

RUN_STATUS_VALUES = (
    "DRAFT",
    "QUEUED",
    "SCHEDULING",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLING",
    "CANCELLED",
    "RETRYING",
)


def upgrade() -> None:
    run_status = postgresql.ENUM(
        *RUN_STATUS_VALUES,
        name="run_status",
        create_type=False,
    )
    run_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "training_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("parameter_schema", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", "version", name="uq_training_templates_key_version"),
    )
    op.create_index(
        "ix_training_templates_enabled_key",
        "training_templates",
        ["enabled", "key"],
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("requested_cpu", sa.Float(), nullable=False),
        sa.Column("requested_memory_mb", sa.Integer(), nullable=False),
        sa.Column("assigned_worker_id", sa.Uuid(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("parent_run_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_message", sa.String(length=2000), nullable=True),
        sa.Column("notes", sa.String(length=4000), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["experiment_id"], ["experiments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["parent_run_id"], ["runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["template_id"], ["training_templates.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runs_created_by", "runs", ["created_by"])
    op.create_index(
        "ix_runs_experiment_created_at", "runs", ["experiment_id", "created_at"]
    )
    op.create_index(
        "ix_runs_status_priority_created_at",
        "runs",
        ["status", "priority", "created_at"],
    )
    op.create_table(
        "run_parameters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "name", name="uq_run_parameters_run_name"),
    )
    op.create_index("ix_run_parameters_run_id", "run_parameters", ["run_id"])
    op.create_table(
        "run_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_run_metrics_run_name_step", "run_metrics", ["run_id", "name", "step"]
    )
    op.create_index(
        "ix_run_metrics_run_recorded_at", "run_metrics", ["run_id", "recorded_at"]
    )
    op.create_table(
        "run_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.String(length=4000), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "sequence_number", name="uq_run_logs_run_sequence"),
    )
    op.create_index(
        "ix_run_logs_run_recorded_at", "run_logs", ["run_id", "recorded_at"]
    )
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=200), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "name", name="uq_artifacts_run_name"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        "ix_artifacts_run_created_at", "artifacts", ["run_id", "created_at"]
    )
    op.create_table(
        "run_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("previous_status", run_status, nullable=True),
        sa.Column("new_status", run_status, nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_run_events_run_created_at", "run_events", ["run_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_run_events_run_created_at", table_name="run_events")
    op.drop_table("run_events")
    op.drop_index("ix_artifacts_run_created_at", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index("ix_run_logs_run_recorded_at", table_name="run_logs")
    op.drop_table("run_logs")
    op.drop_index("ix_run_metrics_run_recorded_at", table_name="run_metrics")
    op.drop_index("ix_run_metrics_run_name_step", table_name="run_metrics")
    op.drop_table("run_metrics")
    op.drop_index("ix_run_parameters_run_id", table_name="run_parameters")
    op.drop_table("run_parameters")
    op.drop_index("ix_runs_status_priority_created_at", table_name="runs")
    op.drop_index("ix_runs_experiment_created_at", table_name="runs")
    op.drop_index("ix_runs_created_by", table_name="runs")
    op.drop_table("runs")
    op.drop_index("ix_training_templates_enabled_key", table_name="training_templates")
    op.drop_table("training_templates")
    postgresql.ENUM(name="run_status").drop(op.get_bind(), checkfirst=True)

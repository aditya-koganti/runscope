"""add workers and resource allocation leases

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None

WORKER_STATUS_VALUES = ("ONLINE", "OFFLINE", "STALE")


def upgrade() -> None:
    worker_status = postgresql.ENUM(
        *WORKER_STATUS_VALUES,
        name="worker_status",
        create_type=False,
    )
    worker_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "workers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", worker_status, nullable=False),
        sa.Column("total_cpu", sa.Float(), nullable=False),
        sa.Column("available_cpu", sa.Float(), nullable=False),
        sa.Column("total_memory_mb", sa.Integer(), nullable=False),
        sa.Column("available_memory_mb", sa.Integer(), nullable=False),
        sa.Column("current_run_count", sa.Integer(), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "ix_workers_status_heartbeat",
        "workers",
        ["status", "last_heartbeat_at"],
    )
    op.create_foreign_key(
        "fk_runs_assigned_worker_id_workers",
        "runs",
        "workers",
        ["assigned_worker_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "resource_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("worker_id", sa.Uuid(), nullable=False),
        sa.Column("cpu", sa.Float(), nullable=False),
        sa.Column("memory_mb", sa.Integer(), nullable=False),
        sa.Column("lease_token", sa.Uuid(), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lease_token"),
    )
    op.create_index(
        "ix_resource_allocations_worker_released",
        "resource_allocations",
        ["worker_id", "released_at"],
    )
    op.create_index(
        "ix_resource_allocations_lease_expires",
        "resource_allocations",
        ["lease_expires_at"],
    )
    op.create_index(
        "uq_resource_allocations_active_run",
        "resource_allocations",
        ["run_id"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_resource_allocations_active_run",
        table_name="resource_allocations",
    )
    op.drop_index(
        "ix_resource_allocations_lease_expires",
        table_name="resource_allocations",
    )
    op.drop_index(
        "ix_resource_allocations_worker_released",
        table_name="resource_allocations",
    )
    op.drop_table("resource_allocations")
    op.drop_constraint(
        "fk_runs_assigned_worker_id_workers",
        "runs",
        type_="foreignkey",
    )
    op.drop_index("ix_workers_status_heartbeat", table_name="workers")
    op.drop_table("workers")
    postgresql.ENUM(name="worker_status").drop(op.get_bind(), checkfirst=True)

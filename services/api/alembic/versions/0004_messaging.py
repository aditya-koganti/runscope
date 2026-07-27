"""add outbox and consumer idempotency

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-26
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(length=200), nullable=False),
        sa.Column("partition_key", sa.String(length=200), nullable=False),
        sa.Column("envelope", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publish_attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_outbox_messages_unpublished_created",
        "outbox_messages",
        ["published_at", "created_at"],
    )
    op.create_table(
        "processed_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("consumer_name", sa.String(length=100), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id", "consumer_name", name="uq_processed_event_consumer"
        ),
    )
    op.create_index(
        "ix_processed_messages_processed_at",
        "processed_messages",
        ["processed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_processed_messages_processed_at", table_name="processed_messages")
    op.drop_table("processed_messages")
    op.drop_index(
        "ix_outbox_messages_unpublished_created", table_name="outbox_messages"
    )
    op.drop_table("outbox_messages")

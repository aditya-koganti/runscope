"""create projects and experiments

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-26
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_projects_created_by_created_at",
        "projects",
        ["created_by", "created_at"],
    )
    op.create_index("ix_projects_name", "projects", ["name"])
    op.create_table(
        "experiments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_experiments_project_name"),
    )
    op.create_index("ix_experiments_created_by", "experiments", ["created_by"])
    op.create_index(
        "ix_experiments_project_created_at",
        "experiments",
        ["project_id", "created_at"],
    )
    op.create_index("ix_experiments_name", "experiments", ["name"])


def downgrade() -> None:
    op.drop_index("ix_experiments_name", table_name="experiments")
    op.drop_index("ix_experiments_project_created_at", table_name="experiments")
    op.drop_index("ix_experiments_created_by", table_name="experiments")
    op.drop_table("experiments")
    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_index("ix_projects_created_by_created_at", table_name="projects")
    op.drop_table("projects")

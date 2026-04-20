"""Add event origin to memory events.

Revision ID: 0004_event_origin
Revises: 0003_mem_units_jobs_audit
Create Date: 2026-04-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_event_origin"
down_revision = "0003_mem_units_jobs_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("memory_events") as batch_op:
        batch_op.add_column(sa.Column("event_origin", sa.String(length=50), nullable=True))

    op.execute("UPDATE memory_events SET event_origin = 'user_input' WHERE event_origin IS NULL")

    with op.batch_alter_table("memory_events") as batch_op:
        batch_op.alter_column("event_origin", existing_type=sa.String(length=50), nullable=False)
        batch_op.create_index("ix_memory_events_event_origin", ["event_origin"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("memory_events") as batch_op:
        batch_op.drop_index("ix_memory_events_event_origin")
        batch_op.drop_column("event_origin")

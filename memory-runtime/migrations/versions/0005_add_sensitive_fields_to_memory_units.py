"""Add sensitive flags to memory units.

Revision ID: 0005_sensitive_mem
Revises: 0004_event_origin
Create Date: 2026-04-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_sensitive_mem"
down_revision = "0004_event_origin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("memory_units") as batch_op:
        batch_op.add_column(sa.Column("is_sensitive", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("sensitivity_reason", sa.String(length=100), nullable=True))

    memory_units = sa.table(
        "memory_units",
        sa.column("is_sensitive", sa.Boolean()),
    )
    op.execute(
        memory_units.update()
        .where(memory_units.c.is_sensitive.is_(None))
        .values(is_sensitive=sa.false())
    )

    with op.batch_alter_table("memory_units") as batch_op:
        batch_op.alter_column("is_sensitive", existing_type=sa.Boolean(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("memory_units") as batch_op:
        batch_op.drop_column("sensitivity_reason")
        batch_op.drop_column("is_sensitive")

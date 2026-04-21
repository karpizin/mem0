"""Add recall-performance indexes for episodes and audit logs.

Revision ID: 0006_recall_perf_idx
Revises: 0005_add_sensitive_fields_to_memory_units
Create Date: 2026-04-21
"""
from __future__ import annotations

from alembic import op


revision = "0006_recall_perf_idx"
down_revision = "0005_sensitive_mem"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_episodes_namespace_created_at",
        "episodes",
        ["namespace_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_episodes_namespace_agent_created_at",
        "episodes",
        ["namespace_id", "agent_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_episodes_namespace_session_created_at",
        "episodes",
        ["namespace_id", "session_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_log_namespace_entity_action",
        "audit_log",
        ["namespace_id", "entity_type", "action", "entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_log_namespace_action_created_at",
        "audit_log",
        ["namespace_id", "action", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_namespace_action_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_namespace_entity_action", table_name="audit_log")
    op.drop_index("ix_episodes_namespace_session_created_at", table_name="episodes")
    op.drop_index("ix_episodes_namespace_agent_created_at", table_name="episodes")
    op.drop_index("ix_episodes_namespace_created_at", table_name="episodes")

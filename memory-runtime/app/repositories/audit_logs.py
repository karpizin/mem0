from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        namespace_id: str,
        agent_id: str | None,
        entity_type: str,
        entity_id: str,
        action: str,
        details_json: dict[str, Any] | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            namespace_id=namespace_id,
            agent_id=agent_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            details_json=details_json or {},
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def feedback_score_by_entity(
        self,
        *,
        namespace_id: str,
        entity_type: str,
        entity_ids: list[str],
    ) -> dict[str, float]:
        if not entity_ids:
            return {}

        stmt = (
            select(
                AuditLog.entity_id,
                func.sum(
                    case(
                        (AuditLog.action == "recall_feedback_positive", 1),
                        (AuditLog.action == "recall_feedback_negative", -1),
                        else_=0,
                    )
                ),
            )
            .where(AuditLog.namespace_id == namespace_id)
            .where(AuditLog.entity_type == entity_type)
            .where(AuditLog.entity_id.in_(entity_ids))
            .where(AuditLog.action.in_(("recall_feedback_positive", "recall_feedback_negative")))
            .group_by(AuditLog.entity_id)
        )
        return {
            entity_id: float(score or 0)
            for entity_id, score in self.session.execute(stmt).all()
        }

    def count_by_action(self, actions: list[str]) -> dict[str, int]:
        if not actions:
            return {}

        stmt = (
            select(AuditLog.action, func.count(AuditLog.id))
            .where(AuditLog.action.in_(actions))
            .group_by(AuditLog.action)
        )
        return {
            action: count
            for action, count in self.session.execute(stmt).all()
        }

    def latest_by_action(
        self,
        *,
        namespace_id: str,
        action: str,
        agent_id: str | None = None,
    ) -> AuditLog | None:
        stmt = (
            select(AuditLog)
            .where(AuditLog.namespace_id == namespace_id)
            .where(AuditLog.action == action)
            .order_by(AuditLog.created_at.desc())
        )
        if agent_id is None:
            stmt = stmt.where(AuditLog.agent_id.is_(None))
        else:
            stmt = stmt.where(AuditLog.agent_id == agent_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def session_only_history(
        self,
        *,
        namespace_id: str,
        merge_key: str,
        kind: str,
        space_type: str,
    ) -> dict[str, int]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.namespace_id == namespace_id)
            .where(AuditLog.action == "memory_candidate_demoted_session_only")
            .order_by(AuditLog.created_at.desc())
        )
        demotion_rows = self.session.execute(stmt).scalars().all()
        matching_episode_ids: list[str] = []
        for row in demotion_rows:
            details = row.details_json or {}
            if details.get("merge_key") != merge_key:
                continue
            if details.get("kind") != kind:
                continue
            if details.get("space_type") != space_type:
                continue
            matching_episode_ids.append(row.entity_id)

        feedback_scores = self.feedback_score_by_entity(
            namespace_id=namespace_id,
            entity_type="episode",
            entity_ids=matching_episode_ids,
        )
        positive_feedback_count = sum(1 for score in feedback_scores.values() if score > 0)
        negative_feedback_count = sum(1 for score in feedback_scores.values() if score < 0)
        net_feedback_score = sum(feedback_scores.values())
        return {
            "demoted_count": len(matching_episode_ids),
            "positive_feedback_count": positive_feedback_count,
            "negative_feedback_count": negative_feedback_count,
            "net_feedback_score": int(net_feedback_score),
        }

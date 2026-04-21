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
        if not self.has_feedback_for_entity_type(namespace_id=namespace_id, entity_type=entity_type):
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

    def has_feedback_for_entity_type(
        self,
        *,
        namespace_id: str,
        entity_type: str,
    ) -> bool:
        stmt = (
            select(AuditLog.id)
            .where(AuditLog.namespace_id == namespace_id)
            .where(AuditLog.entity_type == entity_type)
            .where(AuditLog.action.in_(("recall_feedback_positive", "recall_feedback_negative")))
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none() is not None

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

    def list_by_actions(self, actions: list[str]) -> list[AuditLog]:
        if not actions:
            return []

        stmt = (
            select(AuditLog)
            .where(AuditLog.action.in_(actions))
            .order_by(AuditLog.created_at.asc())
        )
        return self.session.execute(stmt).scalars().all()

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

    def promotion_quality_summary(self) -> dict[str, dict]:
        rows = self.list_by_actions(
            [
                "memory_candidate_promoted",
                "memory_candidate_demoted_session_only",
                "memory_candidate_rejected_low_trust",
            ]
        )
        decisions_by_outcome: dict[str, int] = {
            "promote": 0,
            "session_only": 0,
            "reject": 0,
        }
        promote_reasons: dict[str, int] = {}
        session_only_reasons: dict[str, int] = {}
        reject_reasons: dict[str, int] = {}
        novelty_states: dict[str, int] = {}
        signal_flags: dict[str, int] = {}
        rescue_applied_by_trigger: dict[str, int] = {}
        rescue_blocked_by_reason: dict[str, int] = {}

        for row in rows:
            details = row.details_json or {}
            signals = details.get("signals") or {}
            if row.action == "memory_candidate_promoted":
                outcome = "promote"
                reason = details.get("reason") or "default_promote"
                target = promote_reasons
            elif row.action == "memory_candidate_demoted_session_only":
                outcome = "session_only"
                reason = details.get("reason") or "unknown"
                target = session_only_reasons
            else:
                outcome = "reject"
                reason = details.get("reason") or "unknown"
                target = reject_reasons

            decisions_by_outcome[outcome] = decisions_by_outcome.get(outcome, 0) + 1
            target[reason] = target.get(reason, 0) + 1

            novelty_state = signals.get("novelty_state")
            if isinstance(novelty_state, str):
                novelty_states[novelty_state] = novelty_states.get(novelty_state, 0) + 1

            for signal_name in (
                "low_trust",
                "transient",
                "low_value",
                "weak_candidate",
                "origin_demoted",
                "rescue_applied",
                "rescue_blocked",
            ):
                if signals.get(signal_name):
                    signal_flags[signal_name] = signal_flags.get(signal_name, 0) + 1

            if signals.get("rescue_applied"):
                trigger = signals.get("rescue_trigger")
                if isinstance(trigger, str):
                    rescue_applied_by_trigger[trigger] = rescue_applied_by_trigger.get(trigger, 0) + 1
            if signals.get("rescue_blocked"):
                block_reason = signals.get("rescue_block_reason")
                if isinstance(block_reason, str):
                    rescue_blocked_by_reason[block_reason] = (
                        rescue_blocked_by_reason.get(block_reason, 0) + 1
                    )

        return {
            "decisions_by_outcome": decisions_by_outcome,
            "promote_reasons": dict(sorted(promote_reasons.items())),
            "session_only_reasons": dict(sorted(session_only_reasons.items())),
            "reject_reasons": dict(sorted(reject_reasons.items())),
            "novelty_states": dict(sorted(novelty_states.items())),
            "signal_flags": dict(sorted(signal_flags.items())),
            "rescue": {
                "applied_total": sum(rescue_applied_by_trigger.values()),
                "blocked_total": sum(rescue_blocked_by_reason.values()),
                "applied_by_trigger": dict(sorted(rescue_applied_by_trigger.items())),
                "blocked_by_reason": dict(sorted(rescue_blocked_by_reason.items())),
            },
        }

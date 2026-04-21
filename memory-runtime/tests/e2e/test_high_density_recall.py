from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import Base, get_engine, reset_database_caches
from app.main import create_app
from app.workers.runner import WorkerRunner


def _flatten_brief(brief: dict[str, list[str]]) -> str:
    return "\n".join(item for items in brief.values() for item in items)


class HighDensityRecallE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "high_density_recall.db")
        os.environ["MEMORY_RUNTIME_POSTGRES_DSN"] = f"sqlite+pysqlite:///{self.db_path}"
        os.environ["MEMORY_RUNTIME_AUTO_CREATE_TABLES"] = "true"
        os.environ["MEMORY_RUNTIME_ENV"] = "test"
        get_settings.cache_clear()
        reset_database_caches()
        Base.metadata.create_all(bind=get_engine())
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        for key in (
            "MEMORY_RUNTIME_POSTGRES_DSN",
            "MEMORY_RUNTIME_AUTO_CREATE_TABLES",
            "MEMORY_RUNTIME_ENV",
        ):
            os.environ.pop(key, None)
        get_settings.cache_clear()
        reset_database_caches()

    def _bootstrap_scope(self, *, namespace_name: str, agent_name: str) -> tuple[str, str]:
        response = self.client.post(
            "/v1/adapters/openclaw/bootstrap",
            json={
                "namespace_name": namespace_name,
                "agent_name": agent_name,
                "external_ref": namespace_name,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        return payload["namespace_id"], payload["agent_id"]

    def _ingest_event(
        self,
        *,
        namespace_id: str,
        agent_id: str,
        session_id: str,
        event_type: str,
        space_hint: str,
        role: str,
        content: str,
        event_origin: str | None = None,
    ) -> None:
        response = self.client.post(
            "/v1/adapters/openclaw/events",
            json={
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": session_id,
                "event_type": event_type,
                "space_hint": space_hint,
                "event_origin": event_origin,
                "messages": [{"role": role, "content": content}],
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_adapter_recall_mixes_relevant_slots_with_41_memories(self) -> None:
        namespace_id, agent_id = self._bootstrap_scope(
            namespace_name="openclaw:high-density:41",
            agent_name="planner",
        )
        current_session_id = "run_dense_current"

        self._ingest_event(
            namespace_id=namespace_id,
            agent_id=agent_id,
            session_id="run_core_decision",
            event_type="architecture_decision",
            space_hint="project-space",
            event_origin="agent_output",
            role="assistant",
            content="We decided to keep Postgres and Redis as the durable stack for the memory runtime.",
        )
        self._ingest_event(
            namespace_id=namespace_id,
            agent_id=agent_id,
            session_id="run_core_policy",
            event_type="policy_update",
            space_hint="agent-core",
            event_origin="user_input",
            role="user",
            content="For pilot updates, always lead with the verdict before details.",
        )
        self._ingest_event(
            namespace_id=namespace_id,
            agent_id=agent_id,
            session_id="run_core_context",
            event_type="conversation_turn",
            space_hint="project-space",
            event_origin="agent_output",
            role="assistant",
            content="The dedicated memory worker handles background consolidation jobs for the live pilot.",
        )
        self._ingest_event(
            namespace_id=namespace_id,
            agent_id=agent_id,
            session_id=current_session_id,
            event_type="conversation_turn",
            space_hint="session-space",
            event_origin="user_input",
            role="user",
            content="In the current session we still need the acceptance checklist before tomorrow's pilot demo.",
        )

        for index in range(37):
            self._ingest_event(
                namespace_id=namespace_id,
                agent_id=agent_id,
                session_id=f"run_noise_{index}",
                event_type="conversation_turn",
                space_hint="project-space",
                event_origin="agent_output",
                role="assistant",
                content=(
                    f"Household chatter {index}: bakery snacks, bus times, and a deprecated SQLite side experiment "
                    f"that should not matter for runtime recall."
                ),
            )

        processed = WorkerRunner.run_pending_jobs()
        self.assertGreaterEqual(processed, 41)

        recall = self.client.post(
            "/v1/adapters/openclaw/recall",
            json={
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": current_session_id,
                "query": (
                    "In the current session, what architecture decisions, standing procedures, "
                    "and project context matter before I continue the memory runtime pilot?"
                ),
                "context_budget_tokens": 1000,
            },
        )
        self.assertEqual(recall.status_code, 200)
        payload = recall.json()
        brief = payload["brief"]
        flattened = _flatten_brief(brief)

        self.assertGreaterEqual(payload["trace"]["candidate_count"], 41)
        self.assertLessEqual(payload["trace"]["selected_count"], 4)
        self.assertTrue(any("Postgres and Redis as the durable stack" in item for item in brief["prior_decisions"]))
        self.assertTrue(any("lead with the verdict before details" in item for item in brief["standing_procedures"]))
        self.assertTrue(any("dedicated memory worker handles background consolidation jobs" in item for item in brief["active_project_context"]))
        self.assertTrue(any("acceptance checklist before tomorrow's pilot demo" in item for item in brief["recent_session_carryover"]))
        self.assertNotIn("Household chatter", flattened)
        self.assertNotIn("deprecated SQLite side experiment", flattened)

    def test_adapter_recall_stays_compact_with_120_durable_memories(self) -> None:
        namespace_id, agent_id = self._bootstrap_scope(
            namespace_name="openclaw:high-density:120",
            agent_name="planner",
        )

        self._ingest_event(
            namespace_id=namespace_id,
            agent_id=agent_id,
            session_id="run_arch",
            event_type="architecture_decision",
            space_hint="project-space",
            event_origin="agent_output",
            role="assistant",
            content="The memory runtime should stay Postgres-backed with Redis for queueing and pgvector for retrieval.",
        )
        self._ingest_event(
            namespace_id=namespace_id,
            agent_id=agent_id,
            session_id="run_proc",
            event_type="policy_update",
            space_hint="agent-core",
            event_origin="user_input",
            role="user",
            content="For future pilot reports, lead with the verdict, then the evidence, then the backlog.",
        )
        self._ingest_event(
            namespace_id=namespace_id,
            agent_id=agent_id,
            session_id="run_ops",
            event_type="conversation_turn",
            space_hint="project-space",
            event_origin="agent_output",
            role="assistant",
            content="OpenClaw pilot memory uses a dedicated worker and a runtime service on localhost.",
        )

        for index in range(117):
            self._ingest_event(
                namespace_id=namespace_id,
                agent_id=agent_id,
                session_id=f"run_bulk_noise_{index}",
                event_type="conversation_turn",
                space_hint="project-space",
                event_origin="agent_output",
                role="assistant",
                content=(
                    f"Low-value chatter {index}: maybe rename a scratch variable after the pilot and revisit a bakery list later."
                ),
            )

        processed = WorkerRunner.run_pending_jobs()
        self.assertGreaterEqual(processed, 120)

        recall = self.client.post(
            "/v1/adapters/openclaw/recall",
            json={
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": "run_dense_recall",
                "query": (
                    "What durable runtime architecture, reporting procedure, and operational context matter "
                    "for the memory runtime pilot?"
                ),
                "context_budget_tokens": 800,
            },
        )
        self.assertEqual(recall.status_code, 200)
        payload = recall.json()
        brief = payload["brief"]
        flattened = _flatten_brief(brief)

        self.assertGreaterEqual(payload["trace"]["candidate_count"], 120)
        self.assertLessEqual(payload["trace"]["selected_count"], 3)
        self.assertTrue(any("Postgres-backed with Redis for queueing and pgvector" in item for item in brief["prior_decisions"]))
        self.assertTrue(any("lead with the verdict, then the evidence, then the backlog" in item for item in brief["standing_procedures"]))
        self.assertTrue(any("dedicated worker and a runtime service on localhost" in item for item in brief["active_project_context"]))
        self.assertFalse(brief["recent_session_carryover"])
        self.assertNotIn("Low-value chatter", flattened)
        self.assertNotIn("rename a scratch variable", flattened)

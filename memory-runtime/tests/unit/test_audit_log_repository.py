import os
import tempfile
import unittest

from app.config import get_settings
from app.database import Base, get_engine, get_session_factory, reset_database_caches
from app.repositories.audit_logs import AuditLogRepository


class AuditLogRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "audit_log_repo.db")
        os.environ["MEMORY_RUNTIME_POSTGRES_DSN"] = f"sqlite+pysqlite:///{self.db_path}"
        os.environ["MEMORY_RUNTIME_AUTO_CREATE_TABLES"] = "true"
        os.environ["MEMORY_RUNTIME_ENV"] = "test"
        get_settings.cache_clear()
        reset_database_caches()
        Base.metadata.create_all(bind=get_engine())
        self.session = get_session_factory()()
        self.repo = AuditLogRepository(self.session)

    def tearDown(self) -> None:
        self.session.close()
        self.temp_dir.cleanup()
        for key in (
            "MEMORY_RUNTIME_POSTGRES_DSN",
            "MEMORY_RUNTIME_AUTO_CREATE_TABLES",
            "MEMORY_RUNTIME_ENV",
        ):
            os.environ.pop(key, None)
        get_settings.cache_clear()
        reset_database_caches()

    def test_feedback_score_by_entity_returns_empty_when_namespace_has_no_feedback(self) -> None:
        self.repo.create(
            namespace_id="ns-a",
            agent_id="agent-a",
            entity_type="episode",
            entity_id="episode-a",
            action="memory_candidate_promoted",
        )
        self.session.commit()

        scores = self.repo.feedback_score_by_entity(
            namespace_id="ns-a",
            entity_type="episode",
            entity_ids=["episode-a"],
        )

        self.assertEqual(scores, {})

    def test_feedback_score_by_entity_still_returns_net_scores_when_feedback_exists(self) -> None:
        self.repo.create(
            namespace_id="ns-b",
            agent_id="agent-b",
            entity_type="episode",
            entity_id="episode-b",
            action="recall_feedback_positive",
        )
        self.repo.create(
            namespace_id="ns-b",
            agent_id="agent-b",
            entity_type="episode",
            entity_id="episode-b",
            action="recall_feedback_negative",
        )
        self.repo.create(
            namespace_id="ns-b",
            agent_id="agent-b",
            entity_type="episode",
            entity_id="episode-b",
            action="recall_feedback_positive",
        )
        self.session.commit()

        scores = self.repo.feedback_score_by_entity(
            namespace_id="ns-b",
            entity_type="episode",
            entity_ids=["episode-b"],
        )

        self.assertEqual(scores, {"episode-b": 1.0})

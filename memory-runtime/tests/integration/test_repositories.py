from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, get_engine, get_session_factory, reset_database_caches
from app.models import Agent, Episode, MemoryEvent, MemorySpace, Namespace  # noqa: F401
from app.repositories.episodes import EpisodeRepository
from app.repositories.memory_events import MemoryEventRepository
from app.repositories.agents import AgentRepository
from app.repositories.memory_spaces import MemorySpaceRepository
from app.repositories.namespaces import NamespaceRepository


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "repo.db")
        os.environ["MEMORY_RUNTIME_POSTGRES_DSN"] = f"sqlite+pysqlite:///{self.db_path}"
        get_settings.cache_clear()
        reset_database_caches()
        Base.metadata.create_all(bind=get_engine())
        self.session: Session = get_session_factory()()

    def tearDown(self) -> None:
        self.session.close()
        self.temp_dir.cleanup()
        os.environ.pop("MEMORY_RUNTIME_POSTGRES_DSN", None)
        get_settings.cache_clear()
        reset_database_caches()

    def test_namespace_and_agent_repositories(self) -> None:
        namespaces = NamespaceRepository(self.session)
        agents = AgentRepository(self.session)
        spaces = MemorySpaceRepository(self.session)

        namespace = namespaces.create(
            name="cluster:alpha:shared",
            mode="shared",
            source_systems=["openclaw", "bunkerai"],
        )
        spaces.create(namespace_id=namespace.id, space_type="shared-space", name="Shared Space")
        agent = agents.create(
            namespace_id=namespace.id,
            name="researcher",
            source_system="bunkerai",
        )
        spaces.create(
            namespace_id=namespace.id,
            agent_id=agent.id,
            space_type="agent-core",
            name="Agent Core",
        )
        self.session.commit()

        found_namespace = namespaces.get_by_name("cluster:alpha:shared")
        found_agent = agents.get_by_name(namespace.id, "researcher")
        found_spaces = spaces.list_by_agent(namespace.id, agent.id)

        self.assertIsNotNone(found_namespace)
        self.assertIsNotNone(found_agent)
        self.assertEqual(len(found_spaces), 1)
        self.assertEqual(found_spaces[0].space_type, "agent-core")

    def test_memory_event_and_episode_repositories(self) -> None:
        namespaces = NamespaceRepository(self.session)
        agents = AgentRepository(self.session)
        spaces = MemorySpaceRepository(self.session)
        events = MemoryEventRepository(self.session)
        episodes = EpisodeRepository(self.session)

        namespace = namespaces.create(
            name="openclaw:agent:planner",
            mode="isolated",
            source_systems=["openclaw"],
        )
        agent = agents.create(namespace_id=namespace.id, name="planner", source_system="openclaw")
        session_space = spaces.create(
            namespace_id=namespace.id,
            agent_id=agent.id,
            space_type="session-space",
            name="Session Space",
        )
        event = events.create(
            namespace_id=namespace.id,
            agent_id=agent.id,
            space_id=session_space.id,
            session_id="run_123",
            project_id="mem-runtime",
            source_system="openclaw",
            event_type="conversation_turn",
            event_origin="user_input",
            payload_json={"messages": [{"role": "user", "content": "Continue the plan"}], "metadata": {}},
            event_ts=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            dedupe_key="dedupe-1",
        )
        episode = episodes.create(
            namespace_id=namespace.id,
            agent_id=agent.id,
            space_id=session_space.id,
            session_id="run_123",
            start_event_id=event.id,
            end_event_id=event.id,
            summary="conversation_turn: Continue the plan",
            raw_text="user: Continue the plan",
            token_count=4,
            importance_hint="normal",
        )
        self.session.commit()

        self.assertIsNotNone(event.id)
        self.assertIsNotNone(episode.id)
        self.assertEqual(episode.start_event_id, event.id)

    def test_list_for_recall_prefers_query_relevant_older_rows_with_fetch_cap(self) -> None:
        namespaces = NamespaceRepository(self.session)
        agents = AgentRepository(self.session)
        spaces = MemorySpaceRepository(self.session)
        episodes = EpisodeRepository(self.session)

        namespace = namespaces.create(
            name="openclaw:agent:planner:recall-cap",
            mode="isolated",
            source_systems=["openclaw"],
        )
        agent = agents.create(namespace_id=namespace.id, name="planner", source_system="openclaw")
        project_space = spaces.create(
            namespace_id=namespace.id,
            agent_id=agent.id,
            space_type="project-space",
            name="Project Space",
        )

        baseline = datetime.now(timezone.utc)
        relevant = episodes.create(
            namespace_id=namespace.id,
            agent_id=agent.id,
            space_id=project_space.id,
            session_id="run_relevant",
            start_event_id="event-relevant",
            end_event_id="event-relevant",
            summary="architecture_decision: Keep Postgres and Redis as the runtime baseline.",
            raw_text="assistant: Keep Postgres and Redis as the runtime baseline for the memory service.",
            token_count=12,
            importance_hint="high",
        )
        relevant.created_at = baseline

        for index in range(300):
            noise_time = baseline + timedelta(seconds=index + 1)
            noise = Episode(
                namespace_id=namespace.id,
                agent_id=agent.id,
                space_id=project_space.id,
                session_id=f"run_noise_{index}",
                start_event_id=f"event-noise-{index}",
                end_event_id=f"event-noise-{index}",
                summary=f"conversation_turn: Bakery chatter {index} about errands and temporary scratch ideas.",
                raw_text=f"assistant: Bakery chatter {index} about errands and temporary scratch ideas.",
                token_count=12,
                importance_hint="normal",
                created_at=noise_time,
            )
            self.session.add(noise)

        self.session.commit()

        rows = episodes.list_for_recall(
            namespace_id=namespace.id,
            agent_id=agent.id,
            session_id=None,
            space_types=["project-space"],
            query_tokens=["runtime", "baseline", "postgres", "redis"],
        )

        summaries = [episode.summary for episode, _space_type in rows]
        self.assertLessEqual(len(rows), 256)
        self.assertIn("architecture_decision: Keep Postgres and Redis as the runtime baseline.", summaries)

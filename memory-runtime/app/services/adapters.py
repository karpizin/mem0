from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories.agents import AgentRepository
from app.repositories.episodes import EpisodeRepository
from app.repositories.memory_spaces import MemorySpaceRepository
from app.repositories.memory_units import MemoryUnitRepository
from app.repositories.namespaces import NamespaceRepository
from app.sensitivity import detect_sensitive_reason, format_sensitive_text, should_mask_sensitive_outputs
from app.schemas.adapters import (
    AdapterBootstrapRequest,
    AdapterBootstrapResponse,
    AdapterEventCreate,
    AdapterEventRead,
    AdapterMemoryRead,
    AdapterMemorySearchRequest,
    AdapterMemorySearchResponse,
    AdapterRecallRequest,
    AdapterRecallResponse,
)
from app.schemas.event import EventCreate
from app.schemas.recall import RecallRequest
from app.services.ingestion import IngestionService
from app.services.retrieval import RetrievalCandidate, RetrievalService


@dataclass
class _AdapterMemoryCandidate:
    id: str
    resource_kind: str
    space_type: str
    memory: str
    summary: str
    score: float | None
    created_at: object
    updated_at: object
    metadata: dict[str, str | int | float | bool | None]
    is_sensitive: bool = False
    sensitivity_reason: str | None = None


class AdapterService:
    def __init__(self, session: Session):
        self.session = session
        self.namespaces = NamespaceRepository(session)
        self.agents = AgentRepository(session)
        self.spaces = MemorySpaceRepository(session)
        self.episodes = EpisodeRepository(session)
        self.memory_units = MemoryUnitRepository(session)
        self.ingestion = IngestionService(session)
        self.retrieval = RetrievalService(session)

    def bootstrap(self, adapter_name: str, payload: AdapterBootstrapRequest) -> AdapterBootstrapResponse:
        namespace = self.namespaces.get_by_name(payload.namespace_name)
        if namespace is None:
            namespace = self.namespaces.create(
                name=payload.namespace_name,
                mode="isolated",
                source_systems=[adapter_name],
            )
            self.session.flush()

        if namespace.source_systems and adapter_name not in namespace.source_systems:
            raise ValueError(f"Adapter '{adapter_name}' is not enabled for namespace '{namespace.id}'")

        agent = None
        if payload.external_ref:
            agent = self.agents.get_by_external_ref(namespace.id, payload.external_ref)
        if agent is None:
            agent = self.agents.get_by_name(namespace.id, payload.agent_name)
        if agent is None:
            agent = self.agents.create(
                namespace_id=namespace.id,
                name=payload.agent_name,
                source_system=adapter_name,
                external_ref=payload.external_ref,
            )
            for space_type, name in (
                ("agent-core", "Agent Core"),
                ("project-space", "Project Space"),
                ("session-space", "Session Space"),
            ):
                self.spaces.create(
                    namespace_id=namespace.id,
                    agent_id=agent.id,
                    space_type=space_type,
                    name=name,
                )

        self.session.commit()
        return AdapterBootstrapResponse(
            adapter=adapter_name,
            source_system=adapter_name,
            namespace_id=namespace.id,
            namespace_name=namespace.name,
            agent_id=agent.id,
            agent_name=agent.name,
        )

    def ingest_event(self, adapter_name: str, payload: AdapterEventCreate) -> AdapterEventRead:
        self._validate_adapter_context(
            adapter_name=adapter_name,
            namespace_id=payload.namespace_id,
            agent_id=payload.agent_id,
        )
        event = self.ingestion.ingest_event(
            EventCreate(
                namespace_id=payload.namespace_id,
                agent_id=payload.agent_id,
                session_id=payload.session_id,
                project_id=payload.project_id,
                source_system=adapter_name,
                event_type=payload.event_type,
                event_origin=payload.event_origin,
                timestamp=payload.timestamp,
                space_hint=payload.space_hint,
                messages=payload.messages,
                metadata=payload.metadata,
                dedupe_key=payload.dedupe_key,
            )
        )
        return AdapterEventRead(adapter=adapter_name, source_system=adapter_name, event=event)

    def recall(self, adapter_name: str, payload: AdapterRecallRequest) -> AdapterRecallResponse:
        self._validate_adapter_context(
            adapter_name=adapter_name,
            namespace_id=payload.namespace_id,
            agent_id=payload.agent_id,
        )
        recall_response = self.retrieval.recall(
            RecallRequest(
                namespace_id=payload.namespace_id,
                agent_id=payload.agent_id,
                session_id=payload.session_id,
                query=payload.query,
                context_budget_tokens=payload.context_budget_tokens,
                space_filter=payload.space_filter,
            )
        )
        return AdapterRecallResponse(
            adapter=adapter_name,
            source_system=adapter_name,
            brief=recall_response.brief,
            trace=recall_response.trace,
        )

    def search_memories(self, adapter_name: str, payload: AdapterMemorySearchRequest) -> AdapterMemorySearchResponse:
        self._validate_adapter_context(
            adapter_name=adapter_name,
            namespace_id=payload.namespace_id,
            agent_id=payload.agent_id,
        )

        candidates = (
            self._session_candidates(payload.namespace_id, payload.agent_id, payload.session_id)
            if payload.session_id
            else self._long_term_candidates(payload.namespace_id, payload.agent_id)
        )

        ranked_candidates = RetrievalService.rank_candidates(
            payload.query,
            [
                RetrievalCandidate(
                    episode_id=candidate.id,
                    space_type=candidate.space_type,
                    event_type="external_memory" if candidate.resource_kind == "memory_unit" else "conversation_turn",
                    summary=candidate.summary,
                    raw_text=candidate.memory,
                    importance_hint="medium",
                    created_at=candidate.created_at,
                    session_id=payload.session_id if payload.session_id and candidate.resource_kind == "episode" else None,
                    usefulness_score=0.0,
                    is_sensitive=candidate.is_sensitive,
                    sensitivity_reason=candidate.sensitivity_reason,
                )
                for candidate in candidates
            ],
            active_session_id=payload.session_id,
        )
        score_by_id = {
            candidate.episode_id: score
            for candidate, (score, _recency) in [
                (
                    ranked,
                    self._score_candidate(payload.query, ranked, payload.session_id),
                )
                for ranked in ranked_candidates
            ]
        }
        ranked = sorted(
            candidates,
            key=lambda candidate: score_by_id.get(candidate.id, 0.0),
            reverse=True,
        )[: payload.limit]

        return AdapterMemorySearchResponse(
            adapter=adapter_name,
            source_system=adapter_name,
            results=[
                AdapterMemoryRead(
                    id=candidate.id,
                    memory=self._display_memory(candidate),
                    resource_kind=candidate.resource_kind,
                    space_type=candidate.space_type,
                    score=score_by_id.get(candidate.id),
                    created_at=candidate.created_at,
                    updated_at=candidate.updated_at,
                    metadata=candidate.metadata,
                )
                for candidate in ranked
            ],
        )

    def list_memories(
        self,
        *,
        adapter_name: str,
        namespace_id: str,
        agent_id: str | None,
        session_id: str | None,
    ) -> AdapterMemorySearchResponse:
        self._validate_adapter_context(
            adapter_name=adapter_name,
            namespace_id=namespace_id,
            agent_id=agent_id,
        )
        candidates = (
            self._session_candidates(namespace_id, agent_id, session_id)
            if session_id
            else self._long_term_candidates(namespace_id, agent_id)
        )
        return AdapterMemorySearchResponse(
            adapter=adapter_name,
            source_system=adapter_name,
            results=[
                AdapterMemoryRead(
                    id=candidate.id,
                    memory=self._display_memory(candidate),
                    resource_kind=candidate.resource_kind,
                    space_type=candidate.space_type,
                    score=candidate.score,
                    created_at=candidate.created_at,
                    updated_at=candidate.updated_at,
                    metadata=candidate.metadata,
                )
                for candidate in candidates
            ],
        )

    def get_memory(
        self,
        *,
        adapter_name: str,
        namespace_id: str,
        agent_id: str | None,
        memory_id: str,
    ) -> AdapterMemoryRead:
        self._validate_adapter_context(
            adapter_name=adapter_name,
            namespace_id=namespace_id,
            agent_id=agent_id,
        )
        candidate = self._get_candidate(namespace_id, agent_id, memory_id)
        if candidate is None:
            raise LookupError(f"Memory '{memory_id}' not found")
        return AdapterMemoryRead(
            id=candidate.id,
            memory=self._display_memory(candidate),
            resource_kind=candidate.resource_kind,
            space_type=candidate.space_type,
            score=candidate.score,
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
            metadata=candidate.metadata,
        )

    def delete_memory(
        self,
        *,
        adapter_name: str,
        namespace_id: str,
        agent_id: str | None,
        memory_id: str,
    ) -> None:
        self._validate_adapter_context(
            adapter_name=adapter_name,
            namespace_id=namespace_id,
            agent_id=agent_id,
        )
        memory_row = self.memory_units.get_by_id(memory_id)
        if memory_row is not None and memory_row.namespace_id == namespace_id:
            if agent_id is not None and memory_row.agent_id not in {None, agent_id}:
                raise LookupError(f"Memory '{memory_id}' not found in namespace")
            self.memory_units.delete(memory_row)
            self.session.commit()
            return

        episode = self.episodes.get_by_id(memory_id)
        if episode is not None and episode.namespace_id == namespace_id:
            if agent_id is not None and episode.agent_id not in {None, agent_id}:
                raise LookupError(f"Memory '{memory_id}' not found in namespace")
            self.episodes.delete(episode)
            self.session.commit()
            return
        raise LookupError(f"Memory '{memory_id}' not found")

    def _validate_adapter_context(self, *, adapter_name: str, namespace_id: str, agent_id: str | None) -> None:
        namespace = self.namespaces.get_by_id(namespace_id)
        if namespace is None:
            raise LookupError(f"Namespace '{namespace_id}' not found")

        if namespace.source_systems and adapter_name not in namespace.source_systems:
            raise ValueError(f"Adapter '{adapter_name}' is not enabled for namespace '{namespace_id}'")

        if agent_id is None:
            return

        agent = self.agents.get_by_id(agent_id)
        if agent is None or agent.namespace_id != namespace_id:
            raise LookupError(f"Agent '{agent_id}' not found in namespace")
        if agent.source_system.strip().lower() != adapter_name:
            raise ValueError(f"Agent '{agent_id}' does not belong to adapter '{adapter_name}'")

    def _session_candidates(
        self,
        namespace_id: str,
        agent_id: str | None,
        session_id: str | None,
    ) -> list[_AdapterMemoryCandidate]:
        if session_id is None:
            return []
        rows = self.episodes.list_by_session(
            namespace_id=namespace_id,
            agent_id=agent_id,
            session_id=session_id,
        )
        return [self._episode_candidate(episode=episode, space_type=space_type) for episode, space_type in rows]

    def _long_term_candidates(
        self,
        namespace_id: str,
        agent_id: str | None,
    ) -> list[_AdapterMemoryCandidate]:
        long_term_space_types = ["project-space", "agent-core", "shared-space"]
        memory_rows = self.memory_units.list_active_with_space(
            namespace_id=namespace_id,
            agent_id=agent_id,
            space_types=long_term_space_types,
        )
        return [
            _AdapterMemoryCandidate(
                id=memory.id,
                resource_kind="memory_unit",
                space_type=space_type,
                memory=memory.content,
                summary=memory.summary,
                score=None,
                created_at=memory.created_at,
                updated_at=memory.updated_at,
                metadata={
                    "space_type": space_type,
                    "kind": memory.kind,
                    "scope": memory.scope,
                    "sensitive": memory.is_sensitive,
                    "sensitivity_reason": memory.sensitivity_reason,
                    "masked": memory.is_sensitive and should_mask_sensitive_outputs(),
                },
                is_sensitive=memory.is_sensitive,
                sensitivity_reason=memory.sensitivity_reason,
            )
            for memory, space_type in memory_rows
        ]

    def _get_candidate(
        self,
        namespace_id: str,
        agent_id: str | None,
        memory_id: str,
    ) -> _AdapterMemoryCandidate | None:
        memory_row = self.memory_units.get_with_space(memory_id)
        if memory_row is not None:
            memory, space_type = memory_row
            if memory.namespace_id == namespace_id and (agent_id is None or memory.agent_id in {None, agent_id}):
                return _AdapterMemoryCandidate(
                    id=memory.id,
                    resource_kind="memory_unit",
                    space_type=space_type,
                    memory=memory.content,
                    summary=memory.summary,
                    score=None,
                    created_at=memory.created_at,
                    updated_at=memory.updated_at,
                    metadata={
                        "space_type": space_type,
                        "kind": memory.kind,
                        "scope": memory.scope,
                        "sensitive": memory.is_sensitive,
                        "sensitivity_reason": memory.sensitivity_reason,
                        "masked": memory.is_sensitive and should_mask_sensitive_outputs(),
                    },
                    is_sensitive=memory.is_sensitive,
                    sensitivity_reason=memory.sensitivity_reason,
                )

        episode = self.episodes.get_by_id(memory_id)
        if episode is None or episode.namespace_id != namespace_id:
            return None
        if agent_id is not None and episode.agent_id not in {None, agent_id}:
            return None
        space = self.spaces.get_by_id(episode.space_id) if episode.space_id else None
        space_type = space.space_type if space is not None else "session-space"
        return self._episode_candidate(episode=episode, space_type=space_type)

    @staticmethod
    def _episode_candidate(*, episode, space_type: str) -> _AdapterMemoryCandidate:
        sensitivity_reason = detect_sensitive_reason(episode.raw_text)
        is_sensitive = sensitivity_reason is not None
        return _AdapterMemoryCandidate(
            id=episode.id,
            resource_kind="episode",
            space_type=space_type,
            memory=episode.raw_text,
            summary=episode.summary,
            score=None,
            created_at=episode.created_at,
            updated_at=episode.created_at,
            metadata={
                "session_id": episode.session_id,
                "space_type": space_type,
                "sensitive": is_sensitive,
                "sensitivity_reason": sensitivity_reason,
                "masked": is_sensitive and should_mask_sensitive_outputs(),
            },
            is_sensitive=is_sensitive,
            sensitivity_reason=sensitivity_reason,
        )

    @staticmethod
    def _display_memory(candidate: _AdapterMemoryCandidate) -> str:
        return format_sensitive_text(
            candidate.memory,
            is_sensitive=candidate.is_sensitive,
            masked=candidate.is_sensitive and should_mask_sensitive_outputs(),
        )

    @staticmethod
    def _score_candidate(
        query: str,
        candidate: RetrievalCandidate,
        session_id: str | None,
    ) -> tuple[float, float]:
        ranked = RetrievalService.rank_candidates(query, [candidate], session_id)
        selected = ranked[0]
        overlap = RetrievalService._token_overlap(query, f"{selected.summary} {selected.raw_text}")
        importance = {"high": 2.0, "medium": 1.0, "normal": 0.0}.get(selected.importance_hint, 0.0)
        session_boost = 1.0 if session_id and selected.session_id == session_id else 0.0
        recency = RetrievalService._recency_score(selected.created_at)
        usefulness = selected.usefulness_score * 3.0
        return overlap * 10.0 + importance + session_boost + recency + usefulness, recency

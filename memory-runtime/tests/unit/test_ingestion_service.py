from __future__ import annotations

import unittest

from app.schemas.event import EventMessage
from app.services.ingestion import IngestionService


class IngestionServiceTests(unittest.TestCase):
    def test_normalize_messages_collapses_internal_whitespace(self) -> None:
        messages = [
            EventMessage(role="user", content="  Continue   the   migration   "),
            EventMessage(role="assistant", content=" I   updated   the docs "),
        ]

        normalized = IngestionService.normalize_messages(messages)

        self.assertEqual(
            [message.model_dump() for message in normalized],
            [
                {"role": "user", "content": "Continue the migration"},
                {"role": "assistant", "content": "I updated the docs"},
            ],
        )

    def test_normalize_messages_drops_system_messages_when_turn_is_mixed(self) -> None:
        messages = [
            EventMessage(
                role="system",
                content="Current date: 2026-04-20. Extract durable facts from this conversation.",
            ),
            EventMessage(role="user", content="  Keep Postgres and Redis in the pilot stack. "),
            EventMessage(role="assistant", content=" Noted. "),
        ]

        normalized = IngestionService.normalize_messages(messages)

        self.assertEqual(
            [message.model_dump() for message in normalized],
            [
                {"role": "user", "content": "Keep Postgres and Redis in the pilot stack."},
                {"role": "assistant", "content": "Noted."},
            ],
        )

    def test_compute_dedupe_key_is_deterministic(self) -> None:
        payload = {
            "messages": [{"role": "user", "content": "Continue the plan"}],
            "metadata": {"project_id": "mem-runtime"},
        }

        first = IngestionService.compute_dedupe_key(
            namespace_id="ns-1",
            agent_id="ag-1",
            session_id="run-1",
            source_system="openclaw",
            event_type="conversation_turn",
            event_origin="user_input",
            normalized_payload=payload,
        )
        second = IngestionService.compute_dedupe_key(
            namespace_id="ns-1",
            agent_id="ag-1",
            session_id="run-1",
            source_system="openclaw",
            event_type="conversation_turn",
            event_origin="user_input",
            normalized_payload=payload,
        )

        self.assertEqual(first, second)

    def test_infer_event_origin_prefers_explicit_origin(self) -> None:
        origin = IngestionService.infer_event_origin(
            explicit_origin="recalled_memory",
            event_type="conversation_turn",
            messages=[EventMessage(role="assistant", content="Use the previous brief")],
        )

        self.assertEqual(origin, "recalled_memory")

    def test_infer_event_origin_detects_system_boot(self) -> None:
        origin = IngestionService.infer_event_origin(
            explicit_origin=None,
            event_type="conversation_turn",
            messages=[EventMessage(role="system", content="Bootstrap instructions")],
        )

        self.assertEqual(origin, "system_boot")

    def test_infer_event_origin_defaults_to_user_input_for_mixed_turn(self) -> None:
        origin = IngestionService.infer_event_origin(
            explicit_origin=None,
            event_type="conversation_turn",
            messages=[
                EventMessage(role="user", content="Continue the migration"),
                EventMessage(role="assistant", content="I updated the plan"),
            ],
        )

        self.assertEqual(origin, "user_input")

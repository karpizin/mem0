from __future__ import annotations

from pathlib import Path

from app.mcp_smoke import run_mcp_smoke


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeClient:
    def __init__(self) -> None:
        self._namespace_id = "ns-mcp"
        self._agent_id = "agent-mcp"
        self._event_id = "event-mcp-1"
        self._selected_episode_id = "episode-mcp-1"
        self.post_calls: list[tuple[str, dict[str, object] | None]] = []

    def post(self, path: str, *, json: dict[str, object], headers: dict[str, str] | None = None):
        self.post_calls.append((path, json))
        if path == "/v1/namespaces":
            return _Response({"id": self._namespace_id})
        if path == f"/v1/namespaces/{self._namespace_id}/agents":
            return _Response({"id": self._agent_id})
        if path == "/mcp/openclaw/http/alice":
            method = json["method"]
            request_id = json["id"]
            if method == "initialize":
                return _Response(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"protocolVersion": "2025-03-26"},
                    }
                )
            if method == "tools/list":
                return _Response(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": [
                                {"name": "memory.ingest_event"},
                                {"name": "memory.recall"},
                                {"name": "memory.record_feedback"},
                            ]
                        },
                    }
                )
            if method == "tools/call":
                tool_name = json["params"]["name"]
                if tool_name == "memory.ingest_event":
                    return _Response(
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "structuredContent": {
                                    "event": {"id": self._event_id, "episode_id": self._selected_episode_id},
                                    "guardrails": {"path": "ingestion_pipeline"},
                                }
                            },
                        }
                    )
                if tool_name == "memory.recall":
                    return _Response(
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "structuredContent": {
                                    "brief": {
                                        "critical_facts": [
                                            "The MCP smoke flow verifies initialize, tools/list, ingest_event, recall, and record_feedback."
                                        ],
                                        "active_project_context": [],
                                        "prior_decisions": [],
                                        "standing_procedures": [],
                                        "recent_session_carryover": [],
                                    },
                                    "trace": {"selected_episode_ids": [self._selected_episode_id]},
                                }
                            },
                        }
                    )
                if tool_name == "memory.record_feedback":
                    return _Response(
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "structuredContent": {"feedback": {"recorded_count": 1, "helpful": True}}
                            },
                        }
                    )
        raise AssertionError(f"Unexpected POST {path} {json} {headers}")

    def get(self, path: str):
        if path == "/v1/observability/stats":
            return _Response(
                {
                    "jobs": {"by_status": {"pending": 0, "running": 0, "completed": 2, "failed": 0}},
                    "metrics": {"mcp_requests_total": 5},
                }
            )
        raise AssertionError(f"Unexpected GET {path}")


def test_run_mcp_smoke_covers_initialize_write_recall_feedback(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.pilot_artifacts.ARTIFACT_ROOT", tmp_path / "artifacts")
    drainer_calls: list[str] = []

    report = run_mcp_smoke(
        _FakeClient(),
        artifact_run_name="pytest-mcp-smoke",
        job_drainer=lambda: drainer_calls.append("drain") or 0,
    )

    assert report["initialize_ok"] is True
    assert report["tools_ok"] == {
        "memory.ingest_event": True,
        "memory.recall": True,
        "memory.record_feedback": True,
    }
    assert report["ingested_event_id"] == "event-mcp-1"
    assert report["ingested_episode_id"] == "episode-mcp-1"
    assert report["recall_selected_episode_ids"] == ["episode-mcp-1"]
    assert report["feedback_episode_ids"] == ["episode-mcp-1"]
    assert report["feedback_source"] == "recall_trace"
    assert report["feedback_recorded_count"] == 1
    assert Path(report["artifact_dir"]).exists()
    assert report["jobs_by_status"]["pending"] == 0
    assert report["metrics"]["mcp_requests_total"] == 5
    assert drainer_calls == ["drain"]

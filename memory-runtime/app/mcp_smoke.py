from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from uuid import uuid4

from app.http_client import create_local_runtime_client
from app.pilot_artifacts import default_artifact_run_name, export_trace_bundle

MCP_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def _jsonrpc(method: str, params: dict[str, object] | None = None, *, request_id: int) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }


def _post_mcp(
    client,
    *,
    client_name: str,
    user_id: str,
    method: str,
    params: dict[str, object] | None,
    request_id: int,
) -> dict[str, object]:
    request_payload = _jsonrpc(method, params, request_id=request_id)
    response = client.post(
        f"/mcp/{client_name}/http/{user_id}",
        json=request_payload,
        headers=MCP_HEADERS,
    )
    response.raise_for_status()
    response_payload = response.json()
    if "error" in response_payload:
        raise RuntimeError(
            f"MCP {method} failed with code {response_payload['error']['code']}: "
            f"{response_payload['error']['message']}"
        )
    return response_payload


def _tool_structured_content(payload: dict[str, object], *, tool_name: str) -> dict[str, object]:
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"MCP tool '{tool_name}' returned no JSON-RPC result.")
    if result.get("isError"):
        message = "unknown MCP tool error"
        content = result.get("content")
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict) and isinstance(first.get("text"), str):
                message = first["text"]
        raise RuntimeError(f"MCP tool '{tool_name}' failed: {message}")
    structured = result.get("structuredContent")
    if not isinstance(structured, dict):
        raise RuntimeError(f"MCP tool '{tool_name}' returned no structuredContent.")
    return structured


def _create_scope(client, *, client_name: str, user_id: str, suffix: str) -> dict[str, str]:
    namespace_response = client.post(
        "/v1/namespaces",
        json={
            "name": f"mcp-smoke:{suffix}",
            "mode": "isolated",
            "source_systems": [client_name],
        },
    )
    namespace_response.raise_for_status()
    namespace_id = namespace_response.json()["id"]

    agent_response = client.post(
        f"/v1/namespaces/{namespace_id}/agents",
        json={
            "name": "primary",
            "source_system": client_name,
            "external_ref": f"{user_id}:{suffix}",
        },
    )
    agent_response.raise_for_status()
    agent_id = agent_response.json()["id"]
    return {"namespace_id": namespace_id, "agent_id": agent_id}


def _wait_for_jobs(
    client,
    *,
    poll_seconds: float,
    max_wait_seconds: float,
    job_drainer: Callable[[], int] | None,
) -> dict[str, object]:
    deadline = time.time() + max_wait_seconds
    stats_payload: dict[str, object] = {}
    while True:
        if job_drainer is not None:
            job_drainer()
        stats_response = client.get("/v1/observability/stats")
        stats_response.raise_for_status()
        stats_payload = stats_response.json()
        pending = stats_payload["jobs"]["by_status"].get("pending", 0)
        if pending == 0 or time.time() >= deadline:
            return stats_payload
        time.sleep(poll_seconds)


def run_mcp_smoke(
    client,
    *,
    client_name: str = "openclaw",
    user_id: str = "alice",
    namespace_suffix: str | None = None,
    artifact_run_name: str | None = None,
    poll_seconds: float = 0.5,
    max_wait_seconds: float = 10.0,
    job_drainer: Callable[[], int] | None = None,
) -> dict[str, object]:
    suffix = namespace_suffix or str(uuid4())
    scope = _create_scope(client, client_name=client_name, user_id=user_id, suffix=suffix)
    namespace_id = scope["namespace_id"]
    agent_id = scope["agent_id"]
    session_id = f"mcp-smoke-{suffix}"
    recall_marker = f"mcp-smoke-marker-{suffix[:8]}"
    event_content = (
        f"The MCP smoke flow should verify initialize, tools/list, ingest_event, "
        f"recall, and record_feedback on the live memory runtime. Marker: {recall_marker}."
    )

    initialize_request = _jsonrpc(
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": f"{client_name}-mcp-smoke", "version": "0.1.0"},
        },
        request_id=1,
    )
    initialize_payload = _post_mcp(
        client,
        client_name=client_name,
        user_id=user_id,
        method="initialize",
        params=initialize_request["params"],
        request_id=1,
    )
    tools_request = _jsonrpc("tools/list", None, request_id=2)
    tools_payload = _post_mcp(
        client,
        client_name=client_name,
        user_id=user_id,
        method="tools/list",
        params=None,
        request_id=2,
    )
    ingest_request = _jsonrpc(
        "tools/call",
        {
            "name": "memory.ingest_event",
            "arguments": {
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": session_id,
                "event_type": "architecture_decision",
                "event_origin": "agent_output",
                "space_hint": "project-space",
                "messages": [{"role": "assistant", "content": event_content}],
            },
        },
        request_id=3,
    )
    ingest_payload = _post_mcp(
        client,
        client_name=client_name,
        user_id=user_id,
        method="tools/call",
        params=ingest_request["params"],
        request_id=3,
    )

    stats_payload = _wait_for_jobs(
        client,
        poll_seconds=poll_seconds,
        max_wait_seconds=max_wait_seconds,
        job_drainer=job_drainer,
    )

    recall_request = _jsonrpc(
        "tools/call",
        {
            "name": "memory.recall",
            "arguments": {
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": session_id,
                "query": "What should the MCP smoke flow verify on the live memory runtime?",
                "context_budget_tokens": 700,
            },
        },
        request_id=4,
    )
    recall_request["params"]["arguments"]["query"] = (
        f"Which MCP smoke marker was recorded for {recall_marker}?"
    )
    recall_payload = _post_mcp(
        client,
        client_name=client_name,
        user_id=user_id,
        method="tools/call",
        params=recall_request["params"],
        request_id=4,
    )
    ingest_structured = _tool_structured_content(ingest_payload, tool_name="memory.ingest_event")
    recall_structured = _tool_structured_content(recall_payload, tool_name="memory.recall")
    trace = recall_structured["trace"]
    ingested_event = ingest_structured["event"]
    feedback_episode_ids = trace["selected_episode_ids"][:1]
    feedback_source = "recall_trace"
    if not feedback_episode_ids:
        feedback_episode_ids = [ingested_event["episode_id"]]
        feedback_source = "ingested_event"
    feedback_request = _jsonrpc(
        "tools/call",
        {
            "name": "memory.record_feedback",
            "arguments": {
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "helpful": True,
                "episode_ids": feedback_episode_ids,
                "query": f"Which MCP smoke marker was recorded for {recall_marker}?",
                "notes": "Recorded from MCP smoke script.",
            },
        },
        request_id=5,
    )
    feedback_payload = _post_mcp(
        client,
        client_name=client_name,
        user_id=user_id,
        method="tools/call",
        params=feedback_request["params"],
        request_id=5,
    )

    tool_names = {
        tool["name"] for tool in tools_payload["result"]["tools"]
    }
    recall_brief_items = [
        item
        for slot_items in recall_structured["brief"].values()
        for item in slot_items
    ]
    feedback_structured = _tool_structured_content(
        feedback_payload, tool_name="memory.record_feedback"
    )["feedback"]
    artifact_dir = export_trace_bundle(
        category="mcp-smoke",
        run_name=artifact_run_name or default_artifact_run_name("mcp-smoke"),
        payloads={
            "scope": scope,
            "initialize_request": initialize_request,
            "initialize_response": initialize_payload,
            "tools_request": tools_request,
            "tools_response": tools_payload,
            "ingest_request": ingest_request,
            "ingest_response": ingest_payload,
            "recall_request": recall_request,
            "recall_response": recall_payload,
            "feedback_request": feedback_request,
            "feedback_response": feedback_payload,
            "observability_stats": stats_payload,
        },
    )

    return {
        "namespace_id": namespace_id,
        "agent_id": agent_id,
        "artifact_dir": str(artifact_dir),
        "initialize_ok": initialize_payload["result"]["protocolVersion"] == "2025-03-26",
        "tools_ok": {
            "memory.ingest_event": "memory.ingest_event" in tool_names,
            "memory.recall": "memory.recall" in tool_names,
            "memory.record_feedback": "memory.record_feedback" in tool_names,
        },
        "ingested_event_id": ingested_event["id"],
        "ingested_episode_id": ingested_event["episode_id"],
        "recall_selected_episode_ids": trace["selected_episode_ids"],
        "recall_brief_items": recall_brief_items,
        "feedback_episode_ids": feedback_episode_ids,
        "feedback_source": feedback_source,
        "feedback_recorded_count": feedback_structured["recorded_count"],
        "jobs_by_status": stats_payload["jobs"]["by_status"],
        "metrics": stats_payload["metrics"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an MCP write/read smoke flow against memory-runtime.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--client-name", default="openclaw")
    parser.add_argument("--user-id", default="alice")
    parser.add_argument("--namespace-suffix", default=None)
    parser.add_argument("--artifact-run-name", default=None)
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    parser.add_argument("--max-wait-seconds", type=float, default=10.0)
    args = parser.parse_args(argv)

    with create_local_runtime_client(base_url=args.base_url, timeout=10.0) as client:
        report = run_mcp_smoke(
            client,
            client_name=args.client_name,
            user_id=args.user_id,
            namespace_suffix=args.namespace_suffix,
            artifact_run_name=args.artifact_run_name,
            poll_seconds=args.poll_seconds,
            max_wait_seconds=args.max_wait_seconds,
        )

    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

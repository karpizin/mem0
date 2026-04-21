from __future__ import annotations

import json
import os
import sys
import time
import urllib.request


BASE_URL = os.environ.get("MCP_BASE_URL", "http://127.0.0.1:8080")
CLIENT_NAME = os.environ.get("MCP_CLIENT_NAME", "openclaw")
USER_ID = os.environ.get("MCP_USER_ID", "alice")
NAMESPACE_ID = os.environ.get("NAMESPACE_ID")
AGENT_ID = os.environ.get("AGENT_ID")
SESSION_ID = os.environ.get("SESSION_ID", "mcp-python-smoke")
MARKER = os.environ.get("MARKER", f"mcp-python-marker-{int(time.time())}")


def require(name: str, value: str | None) -> str:
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def mcp_request(method: str, params: dict, request_id: int) -> dict:
    url = f"{BASE_URL}/mcp/{CLIENT_NAME}/http/{USER_ID}"
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        data = json.loads(response.read().decode("utf-8"))
    if "error" in data:
        raise RuntimeError(f"MCP {method} failed: {data['error']}")
    return data


def main() -> int:
    namespace_id = require("NAMESPACE_ID", NAMESPACE_ID)
    agent_id = require("AGENT_ID", AGENT_ID)

    initialize = mcp_request(
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "python-example", "version": "0.1.0"},
        },
        1,
    )
    print("initialize:", json.dumps(initialize["result"], ensure_ascii=False))

    tools = mcp_request("tools/list", {}, 2)
    tool_names = [item["name"] for item in tools["result"]["tools"]]
    print("tools:", tool_names)

    ingest = mcp_request(
        "tools/call",
        {
            "name": "memory.ingest_event",
            "arguments": {
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": SESSION_ID,
                "event_type": "architecture_decision",
                "event_origin": "agent_output",
                "space_hint": "project-space",
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"MCP python example stored marker {MARKER} for runtime smoke verification.",
                    }
                ],
            },
        },
        3,
    )
    ingested_event = ingest["result"]["structuredContent"]["event"]
    print("ingest_event:", json.dumps(ingested_event, ensure_ascii=False))

    recall = mcp_request(
        "tools/call",
        {
            "name": "memory.recall",
            "arguments": {
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": SESSION_ID,
                "query": f"Which MCP python marker was recorded for {MARKER}?",
                "context_budget_tokens": 700,
            },
        },
        4,
    )
    structured = recall["result"]["structuredContent"]
    print("recall trace:", json.dumps(structured["trace"], ensure_ascii=False))
    print("recall brief:", json.dumps(structured["brief"], ensure_ascii=False))

    selected_episode_ids = structured["trace"]["selected_episode_ids"]
    feedback_episode_id = selected_episode_ids[0] if selected_episode_ids else ingested_event["episode_id"]
    feedback = mcp_request(
        "tools/call",
        {
            "name": "memory.record_feedback",
            "arguments": {
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "helpful": True,
                "episode_ids": [feedback_episode_id],
                "query": f"Which MCP python marker was recorded for {MARKER}?",
            },
        },
        5,
    )
    print("record_feedback:", json.dumps(feedback["result"]["structuredContent"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

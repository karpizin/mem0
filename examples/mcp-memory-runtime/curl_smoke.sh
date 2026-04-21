#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${MCP_BASE_URL:-http://127.0.0.1:8080}"
CLIENT_NAME="${MCP_CLIENT_NAME:-openclaw}"
USER_ID="${MCP_USER_ID:-alice}"
NAMESPACE_ID="${NAMESPACE_ID:?NAMESPACE_ID is required}"
AGENT_ID="${AGENT_ID:-}"
SESSION_ID="${SESSION_ID:-mcp-curl-smoke}"
MCP_URL="$BASE_URL/mcp/$CLIENT_NAME/http/$USER_ID"
MARKER="${MARKER:-mcp-curl-marker-$(date +%s)}"

if [[ -z "$AGENT_ID" ]]; then
  echo "AGENT_ID is required for this example." >&2
  exit 1
fi

echo "== initialize =="
curl -s "$MCP_URL" \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": {"name": "curl-example", "version": "0.1.0"}
    }
  }' | jq .

echo "== tools/list =="
curl -s "$MCP_URL" \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }' | jq '.result.tools[].name'

echo "== memory.ingest_event =="
INGEST_RESPONSE="$(curl -s "$MCP_URL" \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"id\": 3,
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"memory.ingest_event\",
      \"arguments\": {
        \"namespace_id\": \"$NAMESPACE_ID\",
        \"agent_id\": \"$AGENT_ID\",
        \"session_id\": \"$SESSION_ID\",
        \"event_type\": \"architecture_decision\",
        \"event_origin\": \"agent_output\",
        \"space_hint\": \"project-space\",
        \"messages\": [
          {
            \"role\": \"assistant\",
            \"content\": \"MCP curl example stored marker $MARKER for runtime smoke verification.\"
          }
        ]
      }
    }
  }")"
echo "$INGEST_RESPONSE" | jq .

EPISODE_ID="$(echo "$INGEST_RESPONSE" | jq -r '.result.structuredContent.event.episode_id')"

echo "== memory.recall =="
RECALL_RESPONSE="$(curl -s "$MCP_URL" \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"id\": 4,
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"memory.recall\",
      \"arguments\": {
        \"namespace_id\": \"$NAMESPACE_ID\",
        \"agent_id\": \"$AGENT_ID\",
        \"session_id\": \"$SESSION_ID\",
        \"query\": \"Which MCP curl marker was recorded for $MARKER?\",
        \"context_budget_tokens\": 700
      }
    }
  }")"
echo "$RECALL_RESPONSE" | jq .

SELECTED_EPISODE_ID="$(echo "$RECALL_RESPONSE" | jq -r '.result.structuredContent.trace.selected_episode_ids[0] // empty')"
FEEDBACK_EPISODE_ID="${SELECTED_EPISODE_ID:-$EPISODE_ID}"

echo "== memory.record_feedback =="
curl -s "$MCP_URL" \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"id\": 5,
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"memory.record_feedback\",
      \"arguments\": {
        \"namespace_id\": \"$NAMESPACE_ID\",
        \"agent_id\": \"$AGENT_ID\",
        \"helpful\": true,
        \"episode_ids\": [\"$FEEDBACK_EPISODE_ID\"],
        \"query\": \"Which MCP curl marker was recorded for $MARKER?\"
      }
    }
  }" | jq .

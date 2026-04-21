const BASE_URL = process.env.MCP_BASE_URL ?? "http://127.0.0.1:8080";
const CLIENT_NAME = process.env.MCP_CLIENT_NAME ?? "openclaw";
const USER_ID = process.env.MCP_USER_ID ?? "alice";
const NAMESPACE_ID = process.env.NAMESPACE_ID;
const AGENT_ID = process.env.AGENT_ID;
const SESSION_ID = process.env.SESSION_ID ?? "mcp-typescript-smoke";
const MARKER = process.env.MARKER ?? `mcp-ts-marker-${Date.now()}`;

function requireEnv(name, value) {
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

async function mcpRequest(method, params, id) {
  const response = await fetch(`${BASE_URL}/mcp/${CLIENT_NAME}/http/${USER_ID}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id,
      method,
      params,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }

  const payload = await response.json();
  if (payload.error) {
    throw new Error(`MCP ${method} failed: ${JSON.stringify(payload.error)}`);
  }
  return payload;
}

async function main() {
  const namespaceId = requireEnv("NAMESPACE_ID", NAMESPACE_ID);
  const agentId = requireEnv("AGENT_ID", AGENT_ID);

  const initialize = await mcpRequest(
    "initialize",
    {
      protocolVersion: "2025-03-26",
      capabilities: {},
      clientInfo: { name: "typescript-example", version: "0.1.0" },
    },
    1,
  );
  console.log("initialize:", JSON.stringify(initialize.result));

  const tools = await mcpRequest("tools/list", {}, 2);
  console.log("tools:", tools.result.tools.map((tool) => tool.name));

  const ingest = await mcpRequest(
    "tools/call",
    {
      name: "memory.ingest_event",
      arguments: {
        namespace_id: namespaceId,
        agent_id: agentId,
        session_id: SESSION_ID,
        event_type: "architecture_decision",
        event_origin: "agent_output",
        space_hint: "project-space",
        messages: [
          {
            role: "assistant",
            content: `MCP TypeScript example stored marker ${MARKER} for runtime smoke verification.`,
          },
        ],
      },
    },
    3,
  );
  const ingestedEvent = ingest.result.structuredContent.event;
  console.log("ingest_event:", JSON.stringify(ingestedEvent));

  const recall = await mcpRequest(
    "tools/call",
    {
      name: "memory.recall",
      arguments: {
        namespace_id: namespaceId,
        agent_id: agentId,
        session_id: SESSION_ID,
        query: `Which MCP TypeScript marker was recorded for ${MARKER}?`,
        context_budget_tokens: 700,
      },
    },
    4,
  );
  console.log("recall trace:", JSON.stringify(recall.result.structuredContent.trace));
  console.log("recall brief:", JSON.stringify(recall.result.structuredContent.brief));

  const selectedEpisodeIds = recall.result.structuredContent.trace.selected_episode_ids;
  const feedbackEpisodeId = selectedEpisodeIds[0] ?? ingestedEvent.episode_id;
  const feedback = await mcpRequest(
    "tools/call",
    {
      name: "memory.record_feedback",
      arguments: {
        namespace_id: namespaceId,
        agent_id: agentId,
        helpful: true,
        episode_ids: [feedbackEpisodeId],
        query: `Which MCP TypeScript marker was recorded for ${MARKER}?`,
      },
    },
    5,
  );
  console.log("record_feedback:", JSON.stringify(feedback.result.structuredContent));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

import type { MemoryItem } from "./types.ts";

const NEW_SESSION_MAX_MEMORIES = 4;
const EXISTING_SESSION_MAX_MEMORIES = 2;
const NEW_SESSION_TOTAL_CHARS = 900;
const EXISTING_SESSION_TOTAL_CHARS = 360;
const NEW_SESSION_MEMORY_MAX_CHARS = 220;
const EXISTING_SESSION_MEMORY_MAX_CHARS = 140;

function compactMemoryText(text: string, maxChars: number): string {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= maxChars) {
    return normalized;
  }
  return `${normalized.slice(0, Math.max(0, maxChars - 1)).trimEnd()}…`;
}

export function buildLegacyRecallContext(params: {
  memories: MemoryItem[];
  userId: string;
  isSubagent: boolean;
  isNewSession: boolean;
  topK: number;
}): { context: string; memoryCount: number; contextChars: number } | undefined {
  const { memories, userId, isSubagent, isNewSession, topK } = params;
  if (memories.length === 0) {
    return undefined;
  }

  const maxMemories = Math.min(
    topK,
    isNewSession ? NEW_SESSION_MAX_MEMORIES : EXISTING_SESSION_MAX_MEMORIES,
  );
  const totalBudget = isNewSession
    ? NEW_SESSION_TOTAL_CHARS
    : EXISTING_SESSION_TOTAL_CHARS;
  const perMemoryBudget = isNewSession
    ? NEW_SESSION_MEMORY_MAX_CHARS
    : EXISTING_SESSION_MEMORY_MAX_CHARS;

  const selected: string[] = [];
  let usedChars = 0;

  for (const memory of memories.slice(0, maxMemories)) {
    const compact = compactMemoryText(memory.memory, perMemoryBudget);
    if (!compact) continue;

    const line = `- ${compact}`;
    if (selected.length > 0 && usedChars + line.length > totalBudget) {
      break;
    }

    selected.push(line);
    usedChars += line.length;
  }

  if (selected.length === 0) {
    return undefined;
  }

  const preamble = isSubagent
    ? `Stored memories for "${userId}". You are a subagent; use only what helps this task.`
    : `Stored memories for "${userId}". Use only what is relevant.`;
  const context =
    `<relevant-memories>\n${preamble}\n` +
    `${selected.join("\n")}\n` +
    `</relevant-memories>`;

  return {
    context,
    memoryCount: selected.length,
    contextChars: context.length,
  };
}

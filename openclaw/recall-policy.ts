export type RecallSkipReason =
  | "acknowledgement_prompt"
  | "recent_recall_cooldown"
  | "short_non_continuity_prompt";

export interface RecallSkipDecision {
  skip: boolean;
  reason?: RecallSkipReason;
  cleanPrompt: string;
}

export interface LegacyRecallPolicyInput {
  prompt: string;
  isNewSession: boolean;
  sessionId?: string;
  lastRecallAtMs?: number;
  nowMs?: number;
}

const CONTINUITY_MARKERS = [
  "remember",
  "remind",
  "earlier",
  "previous",
  "before",
  "we decided",
  "what did we",
  "what was our",
  "last time",
  "continue",
  "context",
  "project",
  "architecture",
  "stack",
  "configuration",
  "config",
  "history",
  "напомни",
  "вспомни",
  "помнишь",
  "раньше",
  "до этого",
  "в прошлый раз",
  "мы решили",
  "продолжим",
  "контекст",
  "проект",
  "архитектур",
  "стек",
  "конфиг",
  "конфигурац",
  "история",
];

const ACKNOWLEDGEMENT_PATTERNS = [
  /^(ok|okay|thanks|thank you|got it|sounds good|roger|great|nice|done|cool)[.! ]*$/i,
  /^(понял|ок|окей|спасибо|хорошо|отлично|супер|ясно|принято|давай|дальше|продолжай)[.! ]*$/i,
];

const RECALL_COOLDOWN_MS = 15_000;

export function stripRecallPolicyNoise(prompt: string): string {
  return prompt
    .replace(/Sender\s*\(untrusted metadata\):\s*```json[\s\S]*?```\s*/gi, "")
    .trim();
}

export function hasContinuityMarkers(prompt: string): boolean {
  const lower = prompt.toLowerCase();
  return CONTINUITY_MARKERS.some((marker) => lower.includes(marker));
}

export function isAcknowledgementLikePrompt(prompt: string): boolean {
  const normalized = prompt.trim().replace(/\s+/g, " ");
  if (!normalized) return false;
  return ACKNOWLEDGEMENT_PATTERNS.some((pattern) => pattern.test(normalized));
}

export function shouldSkipLegacyRecall(
  input: LegacyRecallPolicyInput,
): RecallSkipDecision {
  const cleanPrompt = stripRecallPolicyNoise(input.prompt);
  const nowMs = input.nowMs ?? Date.now();
  const wordCount = cleanPrompt ? cleanPrompt.split(/\s+/).length : 0;
  const continuity = hasContinuityMarkers(cleanPrompt);

  if (!input.isNewSession && isAcknowledgementLikePrompt(cleanPrompt)) {
    return {
      skip: true,
      reason: "acknowledgement_prompt",
      cleanPrompt,
    };
  }

  if (
    !input.isNewSession &&
    input.sessionId &&
    input.lastRecallAtMs !== undefined &&
    nowMs - input.lastRecallAtMs < RECALL_COOLDOWN_MS &&
    !continuity &&
    cleanPrompt.length < 240
  ) {
    return {
      skip: true,
      reason: "recent_recall_cooldown",
      cleanPrompt,
    };
  }

  if (
    !input.isNewSession &&
    !continuity &&
    cleanPrompt.length > 0 &&
    cleanPrompt.length < 40 &&
    wordCount <= 6 &&
    !/[?？]/.test(cleanPrompt)
  ) {
    return {
      skip: true,
      reason: "short_non_continuity_prompt",
      cleanPrompt,
    };
  }

  return { skip: false, cleanPrompt };
}

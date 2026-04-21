type LegacyRecallWork<T> = () => Promise<T>;

const inFlightLegacyRecalls = new Map<string, Promise<unknown>>();
let legacyRecallSequence = 0;

export function nextLegacyRecallId(): string {
  legacyRecallSequence += 1;
  return `legacy-${legacyRecallSequence}`;
}

export function buildLegacyRecallKey(params: {
  sessionId?: string;
  isSubagent: boolean;
  isNewSession: boolean;
  cleanPrompt: string;
}): string {
  const { sessionId, isSubagent, isNewSession, cleanPrompt } = params;
  return [
    sessionId ?? "unknown",
    isSubagent ? "subagent" : "interactive",
    isNewSession ? "new" : "existing",
    cleanPrompt.replace(/\s+/g, " ").trim(),
  ].join("|");
}

export function runLegacyRecallSingleFlight<T>(
  key: string,
  work: LegacyRecallWork<T>,
): { promise: Promise<T>; shared: boolean } {
  const existing = inFlightLegacyRecalls.get(key);
  if (existing) {
    return { promise: existing as Promise<T>, shared: true };
  }

  const pending = work().finally(() => {
    if (inFlightLegacyRecalls.get(key) === pending) {
      inFlightLegacyRecalls.delete(key);
    }
  });
  inFlightLegacyRecalls.set(key, pending);
  return { promise: pending, shared: false };
}

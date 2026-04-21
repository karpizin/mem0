import { describe, expect, it, vi } from "vitest";

import {
  buildLegacyRecallKey,
  nextLegacyRecallId,
  runLegacyRecallSingleFlight,
} from "../legacy-recall-singleflight.ts";

describe("legacy recall single-flight", () => {
  it("builds stable keys for equivalent prompts", () => {
    const a = buildLegacyRecallKey({
      sessionId: "session-1",
      isSubagent: false,
      isNewSession: false,
      cleanPrompt: "What   did   we decide?",
    });
    const b = buildLegacyRecallKey({
      sessionId: "session-1",
      isSubagent: false,
      isNewSession: false,
      cleanPrompt: "What did we decide?",
    });

    expect(a).toBe(b);
  });

  it("shares in-flight work for the same recall key", async () => {
    let executions = 0;
    const work = vi.fn(async () => {
      executions += 1;
      await new Promise((resolve) => setTimeout(resolve, 0));
      return "done";
    });

    const first = runLegacyRecallSingleFlight("k1", work);
    const second = runLegacyRecallSingleFlight("k1", work);

    expect(first.shared).toBe(false);
    expect(second.shared).toBe(true);

    const [a, b] = await Promise.all([first.promise, second.promise]);
    expect(a).toBe("done");
    expect(b).toBe("done");
    expect(executions).toBe(1);
  });

  it("releases the key after completion", async () => {
    const work = vi.fn(async () => "ok");

    await runLegacyRecallSingleFlight("k2", work).promise;
    const next = runLegacyRecallSingleFlight("k2", work);
    await next.promise;

    expect(next.shared).toBe(false);
    expect(work).toHaveBeenCalledTimes(2);
  });

  it("generates monotonic recall ids", () => {
    const first = nextLegacyRecallId();
    const second = nextLegacyRecallId();

    expect(first).not.toBe(second);
    expect(first.startsWith("legacy-")).toBe(true);
    expect(second.startsWith("legacy-")).toBe(true);
  });
});

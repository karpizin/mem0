import { describe, expect, it } from "vitest";

import { buildLegacyRecallContext } from "../legacy-recall.ts";

describe("buildLegacyRecallContext", () => {
  it("keeps existing-session recall compact", () => {
    const result = buildLegacyRecallContext({
      memories: [
        {
          id: "m1",
          memory:
            "We stopped after validating live OpenClaw capture on pilot-user-2 and agreed to resume with continuity reliability tuning on the next run.",
        },
        {
          id: "m2",
          memory:
            "The plugin recall timeout was increased to 15000ms and still occasionally times out on heavy turns.",
        },
        {
          id: "m3",
          memory:
            "This third memory should not fit into the compact existing-session context because we only want the most relevant few lines.",
        },
      ],
      userId: "pilot-user-2",
      isSubagent: false,
      isNewSession: false,
      topK: 5,
    });

    expect(result).toBeDefined();
    expect(result?.memoryCount).toBe(2);
    expect(result?.context).toContain('Stored memories for "pilot-user-2". Use only what is relevant.');
    expect(result?.context).not.toContain("third memory");
    expect(result?.contextChars).toBeLessThanOrEqual(520);
  });

  it("allows a slightly wider budget for new sessions", () => {
    const result = buildLegacyRecallContext({
      memories: Array.from({ length: 6 }, (_, index) => ({
        id: `m${index + 1}`,
        memory: `Memory ${index + 1}: architecture fact about Postgres, Redis, worker topology, and continuity handling.`,
      })),
      userId: "pilot-user-2",
      isSubagent: false,
      isNewSession: true,
      topK: 6,
    });

    expect(result).toBeDefined();
    expect(result?.memoryCount).toBe(4);
    expect(result?.contextChars).toBeLessThanOrEqual(1100);
  });

  it("truncates oversized memories and emits subagent-specific preamble", () => {
    const result = buildLegacyRecallContext({
      memories: [
        {
          id: "m1",
          memory:
            "A".repeat(400) +
            " stored memory that should be clipped when placed into a compact subagent context block.",
        },
      ],
      userId: "pilot-user-2",
      isSubagent: true,
      isNewSession: false,
      topK: 5,
    });

    expect(result).toBeDefined();
    expect(result?.context).toContain("You are a subagent");
    expect(result?.context).toContain("…");
    expect(result?.contextChars).toBeLessThan(320);
  });
});

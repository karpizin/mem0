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

  it("keeps a 40-memory recall set compact and preserves only the top slice", () => {
    const result = buildLegacyRecallContext({
      memories: Array.from({ length: 40 }, (_, index) => ({
        id: `m${index + 1}`,
        memory:
          index === 0
            ? "Critical project memory: keep Postgres, Redis, and pgvector as the runtime baseline."
            : index === 1
              ? "Standing procedure: begin pilot summaries with the verdict, then evidence, then backlog."
              : `Low-value memory ${index + 1}: temporary scratch chatter about renaming a deprecated experiment after the pilot.`,
      })),
      userId: "pilot-user-2",
      isSubagent: false,
      isNewSession: false,
      topK: 40,
    });

    expect(result).toBeDefined();
    expect(result?.memoryCount).toBe(2);
    expect(result?.context).toContain("keep Postgres, Redis, and pgvector");
    expect(result?.context).toContain("begin pilot summaries with the verdict");
    expect(result?.context).not.toContain("Low-value memory 3");
    expect(result?.contextChars).toBeLessThanOrEqual(520);
  });

  it("keeps a 120-memory new-session recall set compact under cold-start budget", () => {
    const result = buildLegacyRecallContext({
      memories: Array.from({ length: 120 }, (_, index) => ({
        id: `m${index + 1}`,
        memory:
          index < 4
            ? `Relevant memory ${index + 1}: durable runtime fact about Postgres, Redis, worker topology, and pilot continuity.`
            : `Noise memory ${index + 1}: short-lived scratch chatter about maybe renaming a variable after the pilot.`,
      })),
      userId: "pilot-user-2",
      isSubagent: false,
      isNewSession: true,
      topK: 120,
    });

    expect(result).toBeDefined();
    expect(result?.memoryCount).toBe(4);
    expect(result?.context).toContain("Relevant memory 1");
    expect(result?.context).toContain("Relevant memory 4");
    expect(result?.context).not.toContain("Noise memory 5");
    expect(result?.contextChars).toBeLessThanOrEqual(1100);
  });
});

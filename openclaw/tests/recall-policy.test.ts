import { describe, expect, it } from "vitest";

import {
  hasContinuityMarkers,
  isAcknowledgementLikePrompt,
  shouldSkipLegacyRecall,
  stripRecallPolicyNoise,
} from "../recall-policy.ts";

describe("recall policy helpers", () => {
  it("strips sender metadata before policy evaluation", () => {
    const prompt =
      'Sender (untrusted metadata): ```json {"foo":"bar"} ```\nRemember our deployment stack';
    expect(stripRecallPolicyNoise(prompt)).toBe("Remember our deployment stack");
  });

  it("detects continuity markers in English and Russian", () => {
    expect(hasContinuityMarkers("Remember what we decided about the stack")).toBe(true);
    expect(hasContinuityMarkers("Напомни, какой у нас стек и архитектура")).toBe(true);
    expect(hasContinuityMarkers("Please write a fresh summary")).toBe(false);
  });

  it("detects acknowledgement-like prompts", () => {
    expect(isAcknowledgementLikePrompt("ok")).toBe(true);
    expect(isAcknowledgementLikePrompt("спасибо")).toBe(true);
    expect(isAcknowledgementLikePrompt("remind me about postgres")).toBe(false);
  });
});

describe("shouldSkipLegacyRecall", () => {
  it("skips acknowledgement prompts on continuing sessions", () => {
    const result = shouldSkipLegacyRecall({
      prompt: "ok",
      isNewSession: false,
      sessionId: "s1",
    });
    expect(result.skip).toBe(true);
    expect(result.reason).toBe("acknowledgement_prompt");
  });

  it("does not skip acknowledgement prompts on a genuinely new session", () => {
    const result = shouldSkipLegacyRecall({
      prompt: "ok",
      isNewSession: true,
      sessionId: "s1",
    });
    expect(result.skip).toBe(false);
  });

  it("skips rapid repeated turns without continuity markers", () => {
    const result = shouldSkipLegacyRecall({
      prompt: "please do it",
      isNewSession: false,
      sessionId: "s1",
      lastRecallAtMs: 10_000,
      nowMs: 20_000,
    });
    expect(result.skip).toBe(true);
    expect(result.reason).toBe("recent_recall_cooldown");
  });

  it("does not skip cooldown turns when continuity markers are present", () => {
    const result = shouldSkipLegacyRecall({
      prompt: "remind me what we decided about postgres earlier",
      isNewSession: false,
      sessionId: "s1",
      lastRecallAtMs: 10_000,
      nowMs: 20_000,
    });
    expect(result.skip).toBe(false);
  });

  it("skips short non-continuity prompts", () => {
    const result = shouldSkipLegacyRecall({
      prompt: "sounds good now",
      isNewSession: false,
      sessionId: "s1",
    });
    expect(result.skip).toBe(true);
    expect(result.reason).toBe("short_non_continuity_prompt");
  });

  it("does not skip short questions", () => {
    const result = shouldSkipLegacyRecall({
      prompt: "what was our stack?",
      isNewSession: false,
      sessionId: "s1",
    });
    expect(result.skip).toBe(false);
  });
});

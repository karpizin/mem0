import { describe, expect, it, vi } from "vitest";

import { runLegacyRecallWithTimeout } from "../legacy-recall-timeout.ts";

describe("legacy recall timeout helper", () => {
  it("does not fire timeout callback after a fast success", async () => {
    vi.useFakeTimers();
    const onTimeout = vi.fn();

    const promise = runLegacyRecallWithTimeout({
      work: async () => "ok",
      timeoutMs: 30_000,
      onTimeout,
    });

    await vi.runAllTimersAsync();
    await expect(promise).resolves.toBe("ok");
    expect(onTimeout).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("returns undefined and fires timeout callback when work hangs", async () => {
    vi.useFakeTimers();
    const onTimeout = vi.fn();

    const promise = runLegacyRecallWithTimeout({
      work: async () => await new Promise<string>(() => undefined),
      timeoutMs: 30_000,
      onTimeout,
    });

    await vi.advanceTimersByTimeAsync(30_000);
    await expect(promise).resolves.toBeUndefined();
    expect(onTimeout).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});

import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationTransportError } from "../src/api/client";
import { loadDirectSideLapConcreteBenchmark } from "../src/fixtures/directSideLapConcreteBenchmarks";
import { useDirectSideLapConcretePreview } from "../src/workspace/directSideLapConcreteWorkflow";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import type { DirectSideLapPreviewResponse } from "../src/api/directSideLapConcreteContracts";
import { directSideLapPreviewFixture } from "./directSideLapConcreteFixtures";

const mocks = vi.hoisted(() => ({ preview: vi.fn() }));

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return { ...actual, previewDirectSideLapConcrete: mocks.preview };
});

function input(
  revision = 1,
  immediate = true,
  validationMessage: string | null = null,
) {
  return {
    request: loadDirectSideLapConcreteBenchmark("US_CUSTOMARY"),
    revision,
    immediate,
    validationMessage,
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  const promise = new Promise<Value>((resolvePromise) => { resolve = resolvePromise; });
  return { promise, resolve };
}

describe("Stage 3.5B preview workflow", () => {
  beforeEach(() => { mocks.preview.mockReset(); });
  afterEach(() => { vi.useRealTimers(); });

  it("accepts an immediate current valid response and retries it", async () => {
    mocks.preview
      .mockResolvedValueOnce(directSideLapPreviewFixture())
      .mockResolvedValueOnce(directSideLapPreviewFixture());
    const value = input();
    const { result } = renderHook(() => useDirectSideLapConcretePreview(value));
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
    expect(result.current.response).not.toBeNull();
    act(() => { result.current.retry(); });
    await waitFor(() => { expect(mocks.preview).toHaveBeenCalledTimes(2); });
  });

  it("debounces, cancels cleanup, and ignores an older response", async () => {
    vi.useFakeTimers();
    const pending = deferred<DirectSideLapPreviewResponse>();
    mocks.preview.mockReturnValueOnce(pending.promise);
    const hook = renderHook(({ value }) => useDirectSideLapConcretePreview(value), {
      initialProps: { value: input(1, false) },
    });
    expect(hook.result.current.state).toBe("PREVIEW_PENDING");
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    const firstSignal = mocks.preview.mock.calls[0]?.[1] as AbortSignal;
    mocks.preview.mockResolvedValueOnce(directSideLapPreviewFixture());
    hook.rerender({ value: input(2, true) });
    expect(firstSignal.aborted).toBe(true);
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    expect(hook.result.current.state).toBe("CURRENT_VALID");
    act(() => { pending.resolve(directSideLapPreviewFixture()); });
    await act(async () => { await Promise.resolve(); });
    expect(hook.result.current.state).toBe("CURRENT_VALID");
    hook.unmount();

    mocks.preview.mockClear();
    const cancelledValue = input(3, false);
    const cancelled = renderHook(() => useDirectSideLapConcretePreview(cancelledValue));
    cancelled.unmount();
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(mocks.preview).not.toHaveBeenCalled();
  });

  it("distinguishes current invalid states with and without a last valid preview", async () => {
    mocks.preview.mockResolvedValueOnce(directSideLapPreviewFixture("INVALID_GEOMETRY"));
    const emptyValue = input();
    const empty = renderHook(() => useDirectSideLapConcretePreview(emptyValue));
    await waitFor(() => { expect(empty.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(empty.result.current.invalidDetail).toContain("ANCHOR_OUTSIDE");
    empty.unmount();

    mocks.preview
      .mockResolvedValueOnce(directSideLapPreviewFixture())
      .mockResolvedValueOnce(directSideLapPreviewFixture("INVALID_GEOMETRY"));
    const retained = renderHook(({ value }) => useDirectSideLapConcretePreview(value), {
      initialProps: { value: input(1) },
    });
    await waitFor(() => { expect(retained.result.current.state).toBe("CURRENT_VALID"); });
    retained.rerender({ value: input(2) });
    await waitFor(() => {
      expect(retained.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    });
    expect(retained.result.current.response).not.toBeNull();

    const emptyReasons = directSideLapPreviewFixture("INVALID_GEOMETRY");
    Object.assign(emptyReasons, { geometry_invalid_reasons: [] });
    Object.assign(emptyReasons.result, { geometry_invalid_reasons: [] });
    mocks.preview.mockResolvedValueOnce(emptyReasons);
    retained.rerender({ value: input(3) });
    await waitFor(() => {
      expect(retained.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    });
    expect(retained.result.current.invalidDetail).toBeNull();
  });

  it("handles local validation before and after a last valid response", async () => {
    const emptyValue = input(1, true, "local");
    const empty = renderHook(() => useDirectSideLapConcretePreview(emptyValue));
    expect(empty.result.current.state).toBe("NO_VALID_PREVIEW");
    expect(empty.result.current.invalidDetail).toBe("local");
    empty.unmount();

    mocks.preview.mockResolvedValueOnce(directSideLapPreviewFixture());
    const retained = renderHook(({ value }) => useDirectSideLapConcretePreview(value), {
      initialProps: { value: input(1) },
    });
    await waitFor(() => { expect(retained.result.current.state).toBe("CURRENT_VALID"); });
    retained.rerender({ value: input(2, true, "local") });
    expect(retained.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
  });

  it("classifies validation, transport, unexpected, and intentional abort failures", async () => {
    mocks.preview.mockRejectedValueOnce(new EvaluationTransportError("VALIDATION", 422, "bad"));
    const invalidValue = input();
    const invalid = renderHook(() => useDirectSideLapConcretePreview(invalidValue));
    await waitFor(() => { expect(invalid.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(invalid.result.current.error).toMatchObject({ kind: "VALIDATION" });
    invalid.unmount();

    mocks.preview.mockRejectedValueOnce("unexpected");
    const unexpectedValue = input();
    const unexpected = renderHook(() => useDirectSideLapConcretePreview(unexpectedValue));
    await waitFor(() => { expect(unexpected.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(unexpected.result.current.error).toMatchObject({ kind: "RESPONSE" });
    unexpected.unmount();

    mocks.preview
      .mockResolvedValueOnce(directSideLapPreviewFixture())
      .mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "offline"));
    const retained = renderHook(({ value }) => useDirectSideLapConcretePreview(value), {
      initialProps: { value: input(1) },
    });
    await waitFor(() => { expect(retained.result.current.state).toBe("CURRENT_VALID"); });
    retained.rerender({ value: input(2) });
    await waitFor(() => {
      expect(retained.result.current.state).toBe("PREVIEW_FAILED_SHOWING_LAST_VALID");
    });
    retained.unmount();

    mocks.preview.mockRejectedValueOnce(new DOMException("cancelled", "AbortError"));
    const abortedValue = input();
    const aborted = renderHook(() => useDirectSideLapConcretePreview(abortedValue));
    await waitFor(() => { expect(mocks.preview).toHaveBeenCalled(); });
    await act(async () => { await Promise.resolve(); });
    expect(aborted.result.current.state).toBe("PREVIEW_PENDING");
    expect(aborted.result.current.error).toBeNull();
  });
});

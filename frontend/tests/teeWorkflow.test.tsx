import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationTransportError } from "../src/api/client";
import type {
  TeeConnectorPreviewResponse,
} from "../src/api/teeContracts";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import { teePreviewErrorDetail, useTeePreview } from "../src/workspace/teeWorkflow";
import type { TeePreviewInput } from "../src/workspace/teeWorkflow";
import { minimalTeeRequest, teePreviewFixture } from "./teeFixtures";

const mocks = vi.hoisted(() => ({ preview: vi.fn() }));

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return { ...actual, previewTeeConnector: mocks.preview };
});

function input(
  revision = 1,
  immediate = true,
  validationMessage: string | null = null,
): TeePreviewInput {
  return {
    request: { ...minimalTeeRequest(), request_id: `TEE-${String(revision)}` },
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

describe("Stage 3.2 Tee live-preview workflow", () => {
  beforeEach(() => { mocks.preview.mockReset(); });
  afterEach(() => { vi.useRealTimers(); });

  it("keeps the last valid response when the current backend result is invalid", async () => {
    mocks.preview
      .mockResolvedValueOnce(teePreviewFixture())
      .mockResolvedValueOnce(teePreviewFixture("INVALID_GEOMETRY"));
    const { result, rerender } = renderHook(({ value }) => useTeePreview(value), {
      initialProps: { value: input(1) },
    });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
    const accepted = result.current.response;
    rerender({ value: input(2) });
    expect(result.current.state).toBe("PREVIEW_PENDING");
    await waitFor(() => {
      expect(result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    });
    expect(result.current.response).toBe(accepted);
    expect(result.current.outdated).toBe(true);
    expect(result.current.acceptedRevision).toBe(1);
  });

  it("retains the preceding preview as outdated while local input is incomplete", async () => {
    mocks.preview.mockResolvedValueOnce(teePreviewFixture());
    const { result, rerender } = renderHook(({ value }) => useTeePreview(value), {
      initialProps: { value: input(1) },
    });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
    rerender({ value: input(2, true, "incomplete") });
    await waitFor(() => {
      expect(result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    });
    expect(result.current.outdated).toBe(true);
    expect(mocks.preview).toHaveBeenCalledTimes(1);
  });

  it("does not update an unmounted incomplete preview", async () => {
    const { unmount } = renderHook(() => useTeePreview(input(1, true, "incomplete")));
    unmount();
    await act(async () => { await Promise.resolve(); });
    expect(mocks.preview).not.toHaveBeenCalled();
  });

  it("debounces typed engineering input by the controlled interval", async () => {
    vi.useFakeTimers();
    mocks.preview.mockResolvedValueOnce(teePreviewFixture());
    const { result } = renderHook(() => useTeePreview(input(1, false)));
    await act(async () => { await Promise.resolve(); });
    expect(result.current.state).toBe("PREVIEW_PENDING");
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(mocks.preview).toHaveBeenCalledTimes(1);
    expect(result.current.state).toMatch(/PREVIEW_PENDING|CURRENT_VALID/);
  });

  it("aborts superseded work and keeps the latest response", async () => {
    const first = deferred<TeeConnectorPreviewResponse>();
    const second = deferred<TeeConnectorPreviewResponse>();
    mocks.preview.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const { result, rerender } = renderHook(({ value }) => useTeePreview(value), {
      initialProps: { value: input(1) },
    });
    const firstSignal = mocks.preview.mock.calls[0]?.[1] as AbortSignal;
    rerender({ value: input(2) });
    expect(firstSignal.aborted).toBe(true);
    const newest = teePreviewFixture();
    newest.request_id = "newest";
    act(() => { second.resolve(newest); });
    await waitFor(() => { expect(result.current.response?.request_id).toBe("newest"); });
    const oldest = teePreviewFixture();
    oldest.request_id = "oldest";
    act(() => { first.resolve(oldest); });
    await act(async () => { await Promise.resolve(); });
    expect(result.current.response?.request_id).toBe("newest");
  });

  it("ignores intentional abort, wraps unexpected errors, and retries", async () => {
    mocks.preview.mockRejectedValueOnce(new DOMException("cancel", "AbortError"));
    const { result, rerender } = renderHook(({ value }) => useTeePreview(value), {
      initialProps: { value: input(1) },
    });
    await act(async () => { await Promise.resolve(); });
    expect(result.current.state).toBe("PREVIEW_PENDING");
    mocks.preview.mockRejectedValueOnce(new Error("unexpected"));
    rerender({ value: input(2) });
    await waitFor(() => { expect(result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(result.current.error).toBeInstanceOf(EvaluationTransportError);
    mocks.preview.mockResolvedValueOnce(teePreviewFixture());
    act(() => { result.current.retry(); });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
  });

  it("preserves an already classified service error", async () => {
    const error = new EvaluationTransportError("VALIDATION", 422, "controlled", null);
    mocks.preview.mockRejectedValueOnce(error);
    const { result } = renderHook(({ value }) => useTeePreview(value), {
      initialProps: { value: input() },
    });
    await waitFor(() => { expect(result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(result.current.error).toBe(error);
  });

  it("classifies validation failure with a prior preview separately from transport failure", async () => {
    mocks.preview.mockResolvedValueOnce(teePreviewFixture());
    const { result, rerender } = renderHook(({ value }) => useTeePreview(value), {
      initialProps: { value: input(1) },
    });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
    mocks.preview.mockRejectedValueOnce(new EvaluationTransportError(
      "VALIDATION",
      422,
      "The server rejected one or more Tee engineering fields.",
      { detail: { code: "CANONICAL_TEE_MAPPING_INVALID", message: "Interface A bolt lines do not fit." } },
    ));
    rerender({ value: input(2) });
    await waitFor(() => {
      expect(result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    });
    expect(result.current.invalidDetail).toBe("Interface A bolt lines do not fit.");
    expect(result.current.response).not.toBeNull();

    mocks.preview.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "offline", null));
    rerender({ value: input(3) });
    await waitFor(() => {
      expect(result.current.state).toBe("PREVIEW_FAILED_SHOWING_LAST_VALID");
    });
  });

  it("extracts direct, structured, and field-addressed server detail with safe fallback", () => {
    const error = (detail: unknown) => new EvaluationTransportError("VALIDATION", 422, "generic", { detail });
    expect(teePreviewErrorDetail(error("Exact server reason."))).toBe("Exact server reason.");
    expect(teePreviewErrorDetail(error({ message: "Interface B reason." }))).toBe("Interface B reason.");
    expect(teePreviewErrorDetail(error([
      null,
      { msg: "Required input.", loc: ["body", "interface_a_layout", 0, "row_count"] },
    ]))).toBe("body → interface_a_layout → 0 → row_count: Required input.");
    expect(teePreviewErrorDetail(error([{ msg: "Malformed input." }]))).toBe("Malformed input.");
    expect(teePreviewErrorDetail(error([{ loc: ["body"] }]))).toBeNull();
    expect(teePreviewErrorDetail(error(42))).toBeNull();
    expect(teePreviewErrorDetail(null)).toBeNull();
  });
});

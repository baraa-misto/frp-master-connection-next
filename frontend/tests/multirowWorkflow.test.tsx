import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationTransportError } from "../src/api/client";
import type {
  MultiRowConnectionRequest,
  MultiRowPreviewResponse,
} from "../src/api/multirowContracts";
import { useMultiRowPreview } from "../src/workspace/multirowWorkflow";
import type { MultiRowPreviewInput } from "../src/workspace/multirowWorkflow";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";

const mocks = vi.hoisted(() => ({ preview: vi.fn() }));

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return { ...actual, previewMultiRow: mocks.preview };
});

function response(status: "VALID" | "INVALID_GEOMETRY" = "VALID"): MultiRowPreviewResponse {
  return {
    api_transport_schema_version: "0.3.0-draft", orchestration_contract_version: "2.5C-RC1", preview_schema_version: "0.2.0-draft", visualization_schema_version: "0.2.0-draft", request_id: "MR", connection_id: "C", geometry_status: status, plan_availability: "READY", method_applicability: "ASCE_PRESCRIPTIVE", qualification: "QUALIFIED_ASCE_PRESCRIPTIVE", warnings: [], preview_fingerprint: "a".repeat(64), resistance_evaluated: false, design_check_ready: status === "VALID", visualization: null, demand_source: "EXPLICIT_RESOLVED_CONNECTION_DEMAND", automatic_demand_result: null,
  };
}

function input(revision = 1, immediate = true, validationMessage: string | null = null): MultiRowPreviewInput {
  return {
    request: { request_id: `MR-${String(revision)}` } as MultiRowConnectionRequest,
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

describe("multi-row live preview workflow", () => {
  beforeEach(() => { mocks.preview.mockReset(); });
  afterEach(() => { vi.useRealTimers(); });

  it("runs immediate preview and maps valid or invalid geometry", async () => {
    mocks.preview.mockResolvedValueOnce(response()).mockResolvedValueOnce(response("INVALID_GEOMETRY"));
    const { result, rerender } = renderHook(({ value }) => useMultiRowPreview(value), {
      initialProps: { value: input(1) },
    });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
    rerender({ value: input(2) });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_INVALID"); });
    expect(result.current.outdated).toBe(false);
  });

  it("retains the previous preview as outdated for local incomplete input", async () => {
    mocks.preview.mockResolvedValueOnce(response());
    const { result, rerender } = renderHook(({ value }) => useMultiRowPreview(value), {
      initialProps: { value: input(1) },
    });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
    rerender({ value: input(2, true, "incomplete") });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_INCOMPLETE"); });
    expect(result.current.outdated).toBe(true);
    expect(mocks.preview).toHaveBeenCalledTimes(1);
  });

  it("does not update an unmounted locally incomplete preview", async () => {
    const { unmount } = renderHook(() => useMultiRowPreview(input(1, true, "incomplete")));
    unmount();
    await act(async () => { await Promise.resolve(); });
    expect(mocks.preview).not.toHaveBeenCalled();
  });

  it("debounces typed input by the controlled interval", async () => {
    vi.useFakeTimers();
    mocks.preview.mockResolvedValueOnce(response());
    const { result } = renderHook(() => useMultiRowPreview(input(1, false)));
    await act(async () => { await Promise.resolve(); });
    expect(result.current.state).toBe("WAITING");
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(mocks.preview).toHaveBeenCalledTimes(1);
    expect(result.current.state).toMatch(/WAITING|PREVIEWING|CURRENT_VALID/);
  });

  it("aborts the prior request and ignores its late response", async () => {
    const first = deferred<MultiRowPreviewResponse>();
    const second = deferred<MultiRowPreviewResponse>();
    mocks.preview.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const { result, rerender } = renderHook(({ value }) => useMultiRowPreview(value), {
      initialProps: { value: input(1) },
    });
    const firstSignal = mocks.preview.mock.calls[0]?.[1] as AbortSignal;
    rerender({ value: input(2) });
    expect(firstSignal.aborted).toBe(true);
    const newest = response();
    newest.request_id = "newest";
    act(() => { second.resolve(newest); });
    await waitFor(() => { expect(result.current.response?.request_id).toBe("newest"); });
    const oldest = response();
    oldest.request_id = "oldest";
    act(() => { first.resolve(oldest); });
    await act(async () => { await Promise.resolve(); });
    expect(result.current.response?.request_id).toBe("newest");
  });

  it("ignores intentional abort and exposes retryable controlled errors", async () => {
    mocks.preview.mockRejectedValueOnce(new DOMException("cancel", "AbortError"));
    const { result, rerender } = renderHook(({ value }) => useMultiRowPreview(value), {
      initialProps: { value: input(1) },
    });
    await act(async () => { await Promise.resolve(); });
    expect(result.current.state).toBe("PREVIEWING");
    mocks.preview.mockRejectedValueOnce(new Error("unexpected"));
    rerender({ value: input(2) });
    await waitFor(() => { expect(result.current.state).toBe("PREVIEW_ERROR"); });
    expect(result.current.error).toBeInstanceOf(EvaluationTransportError);
    mocks.preview.mockResolvedValueOnce(response());
    act(() => { result.current.retry(); });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
  });
});

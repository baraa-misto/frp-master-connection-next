import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationTransportError } from "../src/api/client";
import { loadJ1Benchmark, loadJ1ViewExtents } from "../src/fixtures/j1Benchmarks";
import {
  INPUT_CLASSIFICATION,
  PREVIEW_DEBOUNCE_MS,
  buildSingleBoltPreviewRequest,
  isIntentionalAbort,
  previewStateFromResponse,
  requirePreviewScheduling,
  useCanonicalPreview,
} from "../src/workspace/previewWorkflow";
import type {
  CanonicalPreviewInput,
} from "../src/workspace/previewWorkflow";
import type {
  SingleBoltEvaluationRequest,
  SingleBoltPreviewResponse,
} from "../src/api/contracts";
import { previewResponseFixture } from "./fixtures";

const mocks = vi.hoisted(() => ({ preview: vi.fn() }));

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return { ...actual, previewSingleBolt: mocks.preview };
});

function input(
  revision = 1,
  scheduling: CanonicalPreviewInput["scheduling"] = "IMMEDIATE",
  validationMessage: string | null = null,
): CanonicalPreviewInput {
  return {
    request: loadJ1Benchmark("US_CUSTOMARY"),
    viewExtents: loadJ1ViewExtents("US_CUSTOMARY"),
    revision,
    scheduling,
    validationMessage,
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<Value>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe("canonical preview workflow", () => {
  beforeEach(() => {
    mocks.preview.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("centralizes the four input classes and strips all design-only authority", () => {
    const request = loadJ1Benchmark("US_CUSTOMARY");
    const viewExtents = loadJ1ViewExtents("US_CUSTOMARY");
    const preview = buildSingleBoltPreviewRequest(request, viewExtents);

    expect(new Set(Object.values(INPUT_CLASSIFICATION))).toEqual(new Set([
      "PREVIEW_AFFECTING_ENGINEERING_INPUT",
      "DESIGN_ONLY_ENGINEERING_INPUT",
      "PREVIEW_ONLY_VIEW_EXTENT",
      "PRESENTATION_ONLY_INPUT",
    ]));
    expect(preview.geometry).toBeUndefined();
    expect(preview.geometry_template).toBeDefined();
    expect(preview.view_extents).toEqual(viewExtents);
    expect(preview.fastener_snapshot).toEqual({
      id: request.fastener_snapshot.id,
      washer_geometry: request.fastener_snapshot.washer_geometry,
    });
    expect(preview).not.toHaveProperty("end_use_factors");
    expect(preview).not.toHaveProperty("time_effect_category");
    expect(preview).not.toHaveProperty("published_code_unit_basis");
    expect(preview).not.toHaveProperty("whole_connection_requires_section_2_3_2");

    const explicitGeometry = structuredClone(request);
    explicitGeometry.geometry = {} as NonNullable<SingleBoltEvaluationRequest["geometry"]>;
    delete explicitGeometry.geometry_template;
    const explicitPreview = buildSingleBoltPreviewRequest(explicitGeometry, viewExtents);
    expect(explicitPreview.geometry).toEqual({});
    expect(explicitPreview.geometry_template).toBeUndefined();
    expect(explicitPreview.view_extents).toBeUndefined();
  });

  it.each([
    ["PREVIEW_VALID", "CURRENT_VALID"],
    ["PREVIEW_INVALID_GEOMETRY", "CURRENT_INVALID"],
    ["PREVIEW_INCOMPLETE_INPUT", "CURRENT_INCOMPLETE"],
    ["PREVIEW_UNSUPPORTED", "CURRENT_INCOMPLETE"],
  ] as const)("maps %s to %s", (status, expected) => {
    const response = previewResponseFixture();
    response.geometry_status = status;
    expect(previewStateFromResponse(response)).toBe(expected);
  });

  it("recognizes only DOM AbortError as an intentional cancellation", () => {
    expect(isIntentionalAbort(new DOMException("stopped", "AbortError"))).toBe(true);
    expect(isIntentionalAbort(new DOMException("failed", "NetworkError"))).toBe(false);
    expect(isIntentionalAbort(new Error("AbortError"))).toBe(false);
  });

  it("requires immediate or debounced scheduling for preview-affecting inputs", () => {
    expect(requirePreviewScheduling("IMMEDIATE")).toBe("IMMEDIATE");
    expect(requirePreviewScheduling("DEBOUNCED")).toBe("DEBOUNCED");
    expect(() => requirePreviewScheduling("NONE")).toThrow(
      "Preview-affecting input requires scheduling.",
    );
  });

  it("runs an immediate preview and marks only its matching revision current", async () => {
    mocks.preview.mockResolvedValueOnce(previewResponseFixture());
    const { result } = renderHook(({ value }) => useCanonicalPreview(value), {
      initialProps: { value: input() },
    });

    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
    expect(result.current.currentRevision).toBe(1);
    expect(result.current.outdated).toBe(false);
    expect(mocks.preview).toHaveBeenCalledTimes(1);
    expect(mocks.preview.mock.calls[0]?.[1]).toBeInstanceOf(AbortSignal);
  });

  it("waits exactly for the debounce interval before typed-input preview", async () => {
    vi.useFakeTimers();
    mocks.preview.mockResolvedValueOnce(previewResponseFixture());
    const { result } = renderHook(({ value }) => useCanonicalPreview(value), {
      initialProps: { value: input(2, "DEBOUNCED") },
    });
    await act(async () => { await Promise.resolve(); });
    expect(result.current.state).toBe("WAITING");
    expect(mocks.preview).not.toHaveBeenCalled();

    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS - 1); });
    expect(mocks.preview).not.toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(mocks.preview).toHaveBeenCalledTimes(1);
    await act(async () => { await Promise.resolve(); });
    expect(result.current.state).toBe("CURRENT_VALID");
  });

  it("aborts the prior request and ignores an older response after a newer revision wins", async () => {
    const first = deferred<SingleBoltPreviewResponse>();
    const second = deferred<SingleBoltPreviewResponse>();
    mocks.preview.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const { result, rerender } = renderHook(({ value }) => useCanonicalPreview(value), {
      initialProps: { value: input(1) },
    });
    const firstSignal = mocks.preview.mock.calls[0]?.[1] as AbortSignal;

    rerender({ value: input(2) });
    expect(firstSignal.aborted).toBe(true);
    const newest = previewResponseFixture();
    newest.calculation_id = "newest";
    act(() => { second.resolve(newest); });
    await waitFor(() => { expect(result.current.response?.calculation_id).toBe("newest"); });
    expect(result.current.response?.calculation_id).toBe("newest");
    expect(result.current.currentRevision).toBe(2);

    const oldest = previewResponseFixture();
    oldest.calculation_id = "oldest";
    act(() => { first.resolve(oldest); });
    await act(async () => { await Promise.resolve(); });
    expect(result.current.response?.calculation_id).toBe("newest");
  });

  it("retains the last model as outdated when the next local input is incomplete", async () => {
    mocks.preview.mockResolvedValueOnce(previewResponseFixture());
    const { result, rerender } = renderHook(({ value }) => useCanonicalPreview(value), {
      initialProps: { value: input(1) },
    });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });

    rerender({ value: input(2, "DEBOUNCED", "Incomplete decimal") });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_INCOMPLETE"); });
    expect(result.current.response).not.toBeNull();
    expect(result.current.outdated).toBe(true);
    expect(result.current.error).toBeNull();
    expect(mocks.preview).toHaveBeenCalledTimes(1);
  });

  it("shows controlled preview errors, retains an old model, and retries", async () => {
    const response = previewResponseFixture();
    mocks.preview
      .mockResolvedValueOnce(response)
      .mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "offline"))
      .mockResolvedValueOnce(response);
    const { result, rerender } = renderHook(({ value }) => useCanonicalPreview(value), {
      initialProps: { value: input(1) },
    });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
    rerender({ value: input(2) });
    await waitFor(() => { expect(result.current.state).toBe("PREVIEW_ERROR"); });
    expect(result.current.error).toMatchObject({ kind: "NETWORK" });
    expect(result.current.outdated).toBe(true);

    act(() => { result.current.retry(); });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
    expect(result.current.currentRevision).toBe(2);
    expect(mocks.preview).toHaveBeenCalledTimes(3);
  });

  it("wraps unexpected failures but treats aborted requests as silent", async () => {
    mocks.preview.mockRejectedValueOnce("unexpected");
    const { result, rerender } = renderHook(({ value }) => useCanonicalPreview(value), {
      initialProps: { value: input(1) },
    });
    await waitFor(() => { expect(result.current.state).toBe("PREVIEW_ERROR"); });
    expect(result.current.error).toMatchObject({ kind: "RESPONSE" });
    expect(result.current.outdated).toBe(false);

    mocks.preview.mockRejectedValueOnce(new DOMException("stopped", "AbortError"));
    rerender({ value: input(2) });
    await waitFor(() => { expect(mocks.preview).toHaveBeenCalledTimes(2); });
    await act(async () => { await Promise.resolve(); });
    expect(result.current.error).toBeNull();
    expect(result.current.state).toBe("PREVIEWING");
  });

  it("clears a pending debounce and aborts an in-flight request on cleanup", async () => {
    vi.useFakeTimers();
    const pending = deferred<SingleBoltPreviewResponse>();
    mocks.preview.mockReturnValueOnce(pending.promise);
    const debounced = renderHook(({ value }) => useCanonicalPreview(value), {
      initialProps: { value: input(1, "DEBOUNCED") },
    });
    debounced.unmount();
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(mocks.preview).not.toHaveBeenCalled();

    const immediate = renderHook(({ value }) => useCanonicalPreview(value), {
      initialProps: { value: input(2) },
    });
    const signal = mocks.preview.mock.calls[0]?.[1] as AbortSignal;
    immediate.unmount();
    expect(signal.aborted).toBe(true);
  });
});

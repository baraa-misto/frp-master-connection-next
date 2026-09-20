import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  BEAM_CONCRETE_PAIRED_ANGLE_DESIGN_PATH,
  BEAM_CONCRETE_PAIRED_ANGLE_PREVIEW_PATH,
  EvaluationTransportError,
  evaluateBeamConcretePairedAngle,
  previewBeamConcretePairedAngle,
} from "../src/api/client";
import * as clientModule from "../src/api/client";
import {
  BEAM_CONCRETE_PROFILE_FAMILIES,
  beamConcreteConnectedProfile,
  loadBeamConcretePairedAngleBenchmark,
  loadHistoricalBeamConcretePairedAngleBenchmark,
} from "../src/fixtures/beamConcretePairedAngleBenchmarks";
import { useBeamConcretePairedAnglePreview } from "../src/workspace/beamConcretePairedAngleWorkflow";
import { PAIRED_SURFACES } from "../src/workspace/pairedClipAngleOptions";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import { beamConcreteDesignFixture, beamConcretePreviewFixture } from "./beamConcretePairedAngleFixtures";

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("Stage 3.5A controlled benchmark", () => {
  it("loads exact fresh U.S. and SI fixtures with no user moment surface", () => {
    const us = loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY");
    const si = loadBeamConcretePairedAngleBenchmark("SI");
    expect(us.orchestration_contract_version).toBe("3.5A-R2-RC1");
    expect(us.wall_anchor_pattern).toMatchObject({ row_count: 1, anchors_per_row: 1 });
    expect(us.wall).toMatchObject({ width: { value: "48", unit: "in" }, thickness: { value: "8", unit: "in" } });
    expect(us.beam_profile).not.toHaveProperty("material_kind");
    expect(us.major_shear).toEqual({ value: "-4", unit: "kip" });
    expect(us.minor_shear).toEqual({ value: "0", unit: "kip" });
    expect(us.axial_force).toEqual({ value: "0", unit: "kip" });
    expect(us).not.toHaveProperty("user_moment_hvn");
    expect(si.wall.width).toEqual({ value: "1219.2", unit: "mm" });
    expect(si.common_hole_diameter).toEqual({ value: "14.3002", unit: "mm" });
    us.wall.width.value = "99";
    expect(loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY").wall.width.value).toBe("48");
    expect(loadHistoricalBeamConcretePairedAngleBenchmark("US_CUSTOMARY")).toMatchObject({
      orchestration_contract_version: "3.5A-RC1",
      wall_anchor_pattern: { row_count: 2, anchors_per_row: 2 },
    });
  });

  it("initializes the exact six family-specific connected profiles without stale fields", () => {
    expect(BEAM_CONCRETE_PROFILE_FAMILIES).toEqual([
      "FLAT_PLATE", "ANGLE", "CHANNEL", "WIDE_FLANGE_I",
      "RECTANGULAR_HOLLOW_SECTION", "SOLID_RECTANGULAR_SECTION",
    ]);
    for (const family of BEAM_CONCRETE_PROFILE_FAMILIES) {
      const profile = beamConcreteConnectedProfile("US_CUSTOMARY", family);
      expect(profile.profile_family).toBe(family);
      expect(profile.dimensions.member_length.value).toBe("16");
    }
    expect(beamConcreteConnectedProfile("US_CUSTOMARY", "FLAT_PLATE").dimensions).toEqual({
      member_length: { value: "16", unit: "in" }, width: { value: "6", unit: "in" },
      thickness: { value: "0.5", unit: "in" },
    });
    expect(beamConcreteConnectedProfile("US_CUSTOMARY", "RECTANGULAR_HOLLOW_SECTION")).toMatchObject({
      selected_profile_surface: "Y_POS_FACE",
      dimensions: { depth: { value: "6" }, width: { value: "4" }, wall_thickness: { value: "0.5" } },
    });
    expect(beamConcreteConnectedProfile("US_CUSTOMARY", "SOLID_RECTANGULAR_SECTION").dimensions).not.toHaveProperty("wall_thickness");
  });

  it("fails closed if the shared paired-surface registry has no authorized surface", () => {
    const registry = PAIRED_SURFACES as unknown as Record<string, readonly string[]>;
    const original = registry.FLAT_PLATE;
    try {
      registry.FLAT_PLATE = [];
      expect(() => beamConcreteConnectedProfile("US_CUSTOMARY", "FLAT_PLATE")).toThrow("authorized paired surface");
    } finally {
      registry.FLAT_PLATE = original ?? [];
    }
  });
});

describe("Stage 3.5A API client boundaries", () => {
  beforeEach(() => { vi.stubGlobal("fetch", vi.fn()); });
  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it("posts preview and design only to the two stateless same-origin endpoints", async () => {
    const fetchMock = vi.mocked(fetch);
    const request = loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY");
    const controller = new AbortController();
    fetchMock.mockResolvedValueOnce(response(beamConcretePreviewFixture()));
    await expect(previewBeamConcretePairedAngle(request, controller.signal)).resolves.toMatchObject({ request_id: request.request_id });
    expect(fetchMock).toHaveBeenNthCalledWith(1, BEAM_CONCRETE_PAIRED_ANGLE_PREVIEW_PATH, expect.objectContaining({ method: "POST", credentials: "same-origin", signal: controller.signal }));
    fetchMock.mockResolvedValueOnce(response(beamConcreteDesignFixture()));
    await expect(evaluateBeamConcretePairedAngle(request, controller.signal)).resolves.toMatchObject({ external_design_required: true });
    expect(fetchMock).toHaveBeenNthCalledWith(2, BEAM_CONCRETE_PAIRED_ANGLE_DESIGN_PATH, expect.objectContaining({ method: "POST" }));
  });

  it("rejects malformed successful preview and design responses", async () => {
    const preview = beamConcretePreviewFixture() as unknown as Record<string, unknown>;
    for (const body of [null, {}, { ...preview, api_transport_schema_version: "bad" }, { ...preview, orchestration_contract_version: "bad" }, { ...preview, preview_schema_version: "bad" }, { ...preview, resistance_evaluated: true }, { ...preview, external_design_required: false }, { ...preview, engineering_fingerprint: null }, { ...preview, result: null }]) {
      vi.mocked(fetch).mockResolvedValueOnce(response(body));
      await expect(previewBeamConcretePairedAngle(loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY"), new AbortController().signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    }
    const design = beamConcreteDesignFixture() as unknown as Record<string, unknown>;
    for (const body of [null, {}, { ...design, orchestration_contract_version: "bad" }, { ...design, required_check_status: "PASS" }, { ...design, ordinary_pass_allowed: true }, { ...design, external_design_required: false }, { ...design, result_fingerprint: null }, { ...design, result: null }]) {
      vi.mocked(fetch).mockResolvedValueOnce(response(body));
      await expect(evaluateBeamConcretePairedAngle(loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY"), new AbortController().signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    }
  });

  it("classifies validation, HTTP, network, and intentional abort boundaries", async () => {
    const request = loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY");
    vi.mocked(fetch).mockResolvedValueOnce(response({ detail: "invalid" }, 422));
    await expect(previewBeamConcretePairedAngle(request, new AbortController().signal)).rejects.toMatchObject({ kind: "VALIDATION", status: 422 });
    vi.mocked(fetch).mockResolvedValueOnce(response({ detail: "failed" }, 503));
    await expect(evaluateBeamConcretePairedAngle(request, new AbortController().signal)).rejects.toMatchObject({ kind: "HTTP", status: 503 });
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("offline"));
    await expect(previewBeamConcretePairedAngle(request, new AbortController().signal)).rejects.toMatchObject({ kind: "NETWORK" });
    const abort = new DOMException("aborted", "AbortError");
    vi.mocked(fetch).mockRejectedValueOnce(abort);
    await expect(evaluateBeamConcretePairedAngle(request, new AbortController().signal)).rejects.toBe(abort);
  });
});

describe("Stage 3.5A latest-response-wins preview workflow", () => {
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

  it("accepts immediate valid preview and blocks local invalid input", async () => {
    const spy = vi.spyOn(clientModule, "previewBeamConcretePairedAngle").mockResolvedValueOnce(beamConcretePreviewFixture());
    const request = loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY");
    const valid = renderHook(() => useBeamConcretePairedAnglePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(valid.result.current.state).toBe("CURRENT_VALID"); });
    valid.unmount();
    const blocked = renderHook(() => useBeamConcretePairedAnglePreview({ request, revision: 1, immediate: false, validationMessage: "invalid" }));
    expect(blocked.result.current.state).toBe("NO_VALID_PREVIEW");
    expect(blocked.result.current.invalidDetail).toBe("invalid");
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("debounces invalid and network states while retaining the last valid model and retrying", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(clientModule, "previewBeamConcretePairedAngle");
    spy.mockResolvedValueOnce(beamConcretePreviewFixture());
    let revision = 0;
    const request = loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY");
    const hook = renderHook(() => useBeamConcretePairedAnglePreview({ request, revision, immediate: revision === 0, validationMessage: null }));
    await act(async () => { await Promise.resolve(); });
    expect(hook.result.current.state).toBe("CURRENT_VALID");
    spy.mockResolvedValueOnce(beamConcretePreviewFixture("INVALID_GEOMETRY")); revision = 1; hook.rerender();
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(hook.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    spy.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "offline", null)); revision = 2; hook.rerender();
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(hook.result.current.state).toBe("PREVIEW_FAILED_SHOWING_LAST_VALID");
    spy.mockResolvedValueOnce(beamConcretePreviewFixture()); act(() => { hook.result.current.retry(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(hook.result.current.state).toBe("CURRENT_VALID");
  });

  it("normalizes unexpected failures without accepting superseded responses", async () => {
    const spy = vi.spyOn(clientModule, "previewBeamConcretePairedAngle").mockRejectedValueOnce(new Error("unexpected"));
    const request = loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY");
    const hook = renderHook(() => useBeamConcretePairedAnglePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(hook.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(hook.result.current.error?.message).toMatch(/Unexpected beam-to-concrete/iu);
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("covers empty invalid detail, validation failures, intentional abort, and last-valid local invalidity", async () => {
    const spy = vi.spyOn(clientModule, "previewBeamConcretePairedAngle");
    const request = loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY");
    const invalid = beamConcretePreviewFixture("INVALID_GEOMETRY");
    invalid.geometry_invalid_reasons = [];
    spy.mockResolvedValueOnce(invalid);
    const hook = renderHook((props: { revision: number; validationMessage: string | null }) => useBeamConcretePairedAnglePreview({ request, immediate: true, ...props }), { initialProps: { revision: 0, validationMessage: null as string | null } });
    await waitFor(() => { expect(hook.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(hook.result.current.invalidDetail).toBeNull();
    spy.mockResolvedValueOnce(beamConcretePreviewFixture());
    hook.rerender({ revision: 1, validationMessage: null });
    await waitFor(() => { expect(hook.result.current.state).toBe("CURRENT_VALID"); });
    hook.rerender({ revision: 2, validationMessage: "locally invalid" });
    expect(hook.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");

    spy.mockRejectedValueOnce(new EvaluationTransportError("VALIDATION", 422, "bad request", null));
    hook.rerender({ revision: 3, validationMessage: null });
    await waitFor(() => { expect(hook.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID"); });
    spy.mockRejectedValueOnce(new DOMException("aborted", "AbortError"));
    hook.rerender({ revision: 4, validationMessage: null });
    await waitFor(() => { expect(hook.result.current.state).toBe("PREVIEW_PENDING"); });
  });

  it("ignores a disposed superseded response", async () => {
    let resolveOld: (value: ReturnType<typeof beamConcretePreviewFixture>) => void = () => undefined;
    const spy = vi.spyOn(clientModule, "previewBeamConcretePairedAngle");
    spy.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve; }));
    spy.mockResolvedValueOnce(beamConcretePreviewFixture());
    const request = loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY");
    const hook = renderHook((revision: number) => useBeamConcretePairedAnglePreview({ request, revision, immediate: true, validationMessage: null }), { initialProps: 0 });
    hook.rerender(1);
    await waitFor(() => { expect(hook.result.current.state).toBe("CURRENT_VALID"); });
    resolveOld(beamConcretePreviewFixture());
    await act(async () => { await Promise.resolve(); });
    expect(hook.result.current.response?.request_id).toBe("STAGE-3.5A-R2-G1-US_CUSTOMARY");
  });
});

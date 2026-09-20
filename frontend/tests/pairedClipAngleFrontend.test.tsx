import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  EvaluationTransportError,
  PAIRED_CLIP_ANGLE_DESIGN_PATH,
  PAIRED_CLIP_ANGLE_PREVIEW_PATH,
  evaluatePairedClipAngle,
  previewPairedClipAngle,
} from "../src/api/client";
import * as clientModule from "../src/api/client";
import type { PairedClipAngleRequest } from "../src/api/pairedClipAngleContracts";
import { loadPairedClipAngleBenchmark } from "../src/fixtures/pairedClipAngleBenchmarks";
import { SHARED_SUPPORT_OPTIONS } from "../src/api/sharedSupportContracts";
import { buildPairedClipAngleSceneModel } from "../src/visualization/pairedClipAngleSceneModel";
import { pairedClipAngleValidationMessage } from "../src/workspace/pairedClipAngleValidation";
import {
  PAIRED_PROFILE_FAMILIES,
  PAIRED_SURFACES,
} from "../src/workspace/pairedClipAngleOptions";
import {
  usePairedClipAnglePreview,
  type PairedClipAnglePreviewInput,
} from "../src/workspace/pairedClipAngleWorkflow";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import {
  pairedClipAngleDesignFixture,
  pairedClipAnglePreviewFixture,
} from "./pairedClipAngleFixtures";
import {
  MATERIAL_AXIS_CONNECTED_PROFILE_MATRIX,
  MATERIAL_AXIS_SUPPORT_MATRIX,
  withConnectedMaterialGeometry,
  withSupportMaterialGeometry,
} from "./clipAngleFixtures";

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("controlled Stage 3.3C3 benchmark and validation", () => {
  it("exposes exactly six connected profiles and the seven shared support targets", () => {
    expect(PAIRED_PROFILE_FAMILIES).toEqual([
      "FLAT_PLATE",
      "WIDE_FLANGE_I",
      "CHANNEL",
      "ANGLE",
      "RECTANGULAR_HOLLOW_SECTION",
      "SOLID_RECTANGULAR_SECTION",
    ]);
    expect(PAIRED_SURFACES.ANGLE).toEqual(["LEG_Y_OUTER", "LEG_Z_OUTER"]);
    expect(PAIRED_SURFACES.RECTANGULAR_HOLLOW_SECTION).toHaveLength(4);
    expect(SHARED_SUPPORT_OPTIONS).toHaveLength(7);
    expect(SHARED_SUPPORT_OPTIONS.map((item) => item.id)).not.toContain("W_BEAM_WEB");
  });

  it("loads exact fresh U.S. and SI symmetric pair fixtures", () => {
    const us = loadPairedClipAngleBenchmark("US_CUSTOMARY");
    const si = loadPairedClipAngleBenchmark("SI");
    expect(us.orchestration_contract_version).toBe("3.3C3-RC1");
    expect(us.global_force.z).toBe("4");
    expect(us.global_reference_point.x).toBe("0");
    expect(us.connected_member_profile.dimensions.thickness).toEqual({ value: "0.5", unit: "in" });
    expect(us.support_profile.flange_width).toEqual({ value: "10", unit: "in" });
    expect(si.global_force.z).toBe("17.792886461042");
    expect(si.support_profile.flange_width).toEqual({ value: "254", unit: "mm" });
    expect(us).not.toHaveProperty("hand");
    expect(us).not.toHaveProperty("interface_a_layout");
    us.common_member_layout.pitch.value = "99";
    expect(loadPairedClipAngleBenchmark("US_CUSTOMARY").common_member_layout.pitch.value).toBe("2");
  });

  it("fails closed on unsupported profiles, dimensions, counts, and trim inputs", () => {
    const request = loadPairedClipAngleBenchmark("US_CUSTOMARY");
    expect(pairedClipAngleValidationMessage(request)).toBeNull();
    request.connected_member_profile.profile_family = "ROUND_HOLLOW_SECTION" as PairedClipAngleRequest["connected_member_profile"]["profile_family"];
    expect(pairedClipAngleValidationMessage(request)).toMatch(/six authorized planar/iu);
    request.connected_member_profile.profile_family = "FLAT_PLATE";
    request.connector_dimensions.thickness.value = "0";
    expect(pairedClipAngleValidationMessage(request)).toMatch(/finite and positive/iu);
    request.connector_dimensions.thickness.value = "0.5";
    request.common_member_layout.row_count = 0;
    expect(pairedClipAngleValidationMessage(request)).toMatch(/positive integer/iu);
    request.common_member_layout.row_count = 2;
    request.mirrored_support_layout.bolts_per_row = 0;
    expect(pairedClipAngleValidationMessage(request)).toMatch(/positive integer/iu);
    request.mirrored_support_layout.bolts_per_row = 2;
    request.connected_member_end_trim_enabled = true;
    request.connected_member_end_clearance = null;
    expect(pairedClipAngleValidationMessage(request)).toMatch(/nonnegative clearance/iu);
    request.connected_member_end_clearance = { value: "-1", unit: "in" };
    expect(pairedClipAngleValidationMessage(request)).toMatch(/nonnegative clearance/iu);
  });
});

describe("paired API client boundaries", () => {
  beforeEach(() => { vi.stubGlobal("fetch", vi.fn()); });
  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it("posts strict preview and design requests to their stateless endpoints", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response(pairedClipAnglePreviewFixture()));
    const request = loadPairedClipAngleBenchmark("US_CUSTOMARY");
    const controller = new AbortController();
    await expect(previewPairedClipAngle(request, controller.signal)).resolves.toMatchObject({ request_id: request.request_id });
    expect(fetchMock).toHaveBeenNthCalledWith(1, PAIRED_CLIP_ANGLE_PREVIEW_PATH, expect.objectContaining({ method: "POST", credentials: "same-origin", signal: controller.signal }));
    fetchMock.mockResolvedValueOnce(response(pairedClipAngleDesignFixture()));
    await expect(evaluatePairedClipAngle(request, controller.signal)).resolves.toMatchObject({ required_check_status: "NOT_EVALUATED" });
    expect(fetchMock).toHaveBeenNthCalledWith(2, PAIRED_CLIP_ANGLE_DESIGN_PATH, expect.objectContaining({ method: "POST" }));
  });

  it("rejects every unsupported paired preview response boundary", async () => {
    const good = pairedClipAnglePreviewFixture() as unknown as Record<string, unknown>;
    const invalid: unknown[] = [null, {}, { ...good, api_transport_schema_version: "bad" }, { ...good, orchestration_contract_version: "bad" }, { ...good, preview_schema_version: "bad" }, { ...good, geometry_status: "bad" }, { ...good, resistance_evaluated: true }, { ...good, ordinary_pass_allowed: true }, { ...good, result: null }];
    for (const body of invalid) {
      vi.mocked(fetch).mockResolvedValueOnce(response(body));
      await expect(previewPairedClipAngle(loadPairedClipAngleBenchmark("US_CUSTOMARY"), new AbortController().signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    }
  });

  it("rejects every unsupported paired design response boundary", async () => {
    const good = pairedClipAngleDesignFixture() as unknown as Record<string, unknown>;
    const invalid: unknown[] = [null, {}, { ...good, api_transport_schema_version: "bad" }, { ...good, orchestration_contract_version: "bad" }, { ...good, required_check_status: "PASS" }, { ...good, ordinary_pass_allowed: true }, { ...good, result_fingerprint: null }, { ...good, result: null }];
    for (const body of invalid) {
      vi.mocked(fetch).mockResolvedValueOnce(response(body));
      await expect(evaluatePairedClipAngle(loadPairedClipAngleBenchmark("US_CUSTOMARY"), new AbortController().signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    }
  });
});

describe("backend-authored paired scene adapter", () => {
  it("renders two real angles, three groups, four contacts, and complete embedded axes", () => {
    const visualization = pairedClipAnglePreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Paired fixture visualization required.");
    const model = buildPairedClipAngleSceneModel(visualization);
    expect(model.boxes.filter((box) => box.ownerId === "POSITIVE_CLIP_ANGLE")).toHaveLength(2);
    expect(model.boxes.filter((box) => box.ownerId === "NEGATIVE_CLIP_ANGLE")).toHaveLength(2);
    expect(new Set(model.cylinders.map((item) => item.interfaceId))).toEqual(new Set(["COMMON_MEMBER_THROUGH_BOLT_GROUP", "POSITIVE_SUPPORT_BOLT_GROUP", "NEGATIVE_SUPPORT_BOLT_GROUP"]));
    expect(model.zones).toHaveLength(4);
    expect(model.zones.filter((zone) => zone.interfaceId === "COMMON_MEMBER_THROUGH_BOLT_GROUP")).toHaveLength(2);
    expect(model.materialAxes).toHaveLength(8);
    expect(model.materialAxes.filter((axis) => axis.presentation === null).map(
      (axis) => `${axis.componentId}:${axis.elementId}:${axis.materialRegionId}`,
    )).toEqual([]);
    expect(model.materialAxes.filter((axis) => axis.componentId === "POSITIVE_CLIP_ANGLE")
      .map((axis) => axis.elementId)).toEqual(["CONNECTED_MEMBER_LEG", "SUPPORT_LEG"]);
    expect(model.materialAxes.filter((axis) => axis.componentId === "NEGATIVE_CLIP_ANGLE")
      .map((axis) => axis.elementId)).toEqual(["CONNECTED_MEMBER_LEG", "SUPPORT_LEG"]);
    expect(model.materialAxes.filter(
      (axis) => axis.componentId === "clip-angle-connected-member",
    )).toHaveLength(1);
    expect(model.materialAxes.filter(
      (axis) => axis.componentId === "clip-angle-support",
    )).toHaveLength(3);
    expect(new Set(model.materialAxes.map(
      (axis) => `${axis.componentId}:${axis.elementId}:${axis.materialRegionId}`,
    )).size).toBe(8);
    expect(model.frames[0]).toMatchObject({ id: "PAIRED_CLIP_ANGLE_FRAME", ownerId: "SYMMETRIC_PAIRED_CLIP_ANGLES" });
    expect(model.appliedArrows.find((arrow) => arrow.component === "FZ")?.signedValue).toBe(4);
  });

  it.each(MATERIAL_AXIS_SUPPORT_MATRIX)(
    "binds paired $targetId supporting-member regions without losing mirrored axes",
    (entry) => {
      const source = pairedClipAnglePreviewFixture().result.visualization;
      if (source === null) throw new Error("Paired fixture visualization required.");
      const visualization = withSupportMaterialGeometry(source, entry);
      const model = buildPairedClipAngleSceneModel(visualization);
      const support = model.materialAxes.filter(
        (value) => value.componentId === "clip-angle-support",
      );

      expect(support.map((value) => value.elementId)).toEqual(entry.elements);
      expect(support.every((value) => value.presentation !== null)).toBe(true);
      expect(model.materialAxes.filter(
        (value) => value.componentId === "POSITIVE_CLIP_ANGLE",
      )).toHaveLength(2);
      expect(model.materialAxes.filter(
        (value) => value.componentId === "NEGATIVE_CLIP_ANGLE",
      )).toHaveLength(2);
      expect(support.some((value) => value.elementId === "CAVITY")).toBe(false);
    },
  );

  it.each(MATERIAL_AXIS_CONNECTED_PROFILE_MATRIX)(
    "binds every paired $family connected-member material region",
    (entry) => {
      const source = pairedClipAnglePreviewFixture().result.visualization;
      if (source === null) throw new Error("Paired fixture visualization required.");
      const visualization = withConnectedMaterialGeometry(source, entry);
      const connected = buildPairedClipAngleSceneModel(visualization).materialAxes.filter(
        (value) => value.componentId === "clip-angle-connected-member",
      );

      expect(connected.map((value) => value.elementId)).toEqual(entry.elements);
      expect(connected.every((value) => value.presentation !== null)).toBe(true);
      expect(connected.some((value) => value.elementId === "CAVITY")).toBe(false);
    },
  );

  it("uses backend full-through endpoints for one common RHS shank and external washers", () => {
    const visualization = pairedClipAnglePreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Paired fixture visualization required.");
    const first = visualization.common_member_bolts[0];
    if (first === undefined) throw new Error("Common paired bolt required.");
    const model = buildPairedClipAngleSceneModel({
      ...visualization,
      support_target_id: "RECTANGULAR_HOLLOW_COLUMN_WALL",
      rectangular_full_through_paths: [{
        path: {
          bolt_id: first.bolt_id,
          segments: [
            { kind: "MATERIAL_LAYER", identity: "POSITIVE_CLIP_CONNECTED_LEG", length: "0.5" },
            { kind: "MATERIAL_LAYER", identity: "RHS_NEAR_WALL", length: "0.5" },
            { kind: "FREE_SHANK_SPAN", identity: "RHS_CAVITY", length: "5" },
            { kind: "MATERIAL_LAYER", identity: "RHS_FAR_WALL", length: "0.5" },
            { kind: "MATERIAL_LAYER", identity: "NEGATIVE_CLIP_CONNECTED_LEG", length: "0.5" },
          ],
        },
        hardware: {
          bolt_id: first.bolt_id,
          shank_length: "7",
          head_location: "EXTERIOR_NEAR_SIDE",
          nut_location: "EXTERIOR_FAR_SIDE",
          washer_locations: ["EXTERIOR_NEAR_SIDE", "EXTERIOR_FAR_SIDE"],
          physical_bolt_count: 1,
          continuous_shank_count: 1,
          internal_hardware_count: 0,
        },
        physical_start_point: { x: "4", y: "1.25", z: "-1" },
        physical_end_point: { x: "-4", y: "1.25", z: "-1" },
        geometry_valid: true,
        path_fingerprint: "9".repeat(64),
      }],
    });
    const common = model.cylinders.filter(
      (item) => item.ownerBoltId.endsWith(first.bolt_id),
    );
    expect(common.filter((item) => item.kind === "BOLT")).toEqual([
      expect.objectContaining({ start: { x: 4, y: 1.25, z: -1 }, end: { x: -4, y: 1.25, z: -1 } }),
    ]);
    expect(common.filter((item) => item.kind === "BOLT")).toHaveLength(1);
  });
});

describe("paired latest-response-wins workflow", () => {
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

  it("accepts an immediate valid preview and reports current state", async () => {
    vi.spyOn(clientModule, "previewPairedClipAngle").mockResolvedValueOnce(pairedClipAnglePreviewFixture());
    const input: PairedClipAnglePreviewInput = { request: loadPairedClipAngleBenchmark("US_CUSTOMARY"), revision: 0, immediate: true, validationMessage: null };
    const { result } = renderHook(() => usePairedClipAnglePreview(input));
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
    expect(result.current.acceptedRevision).toBe(0);
    expect(result.current.outdated).toBe(false);
  });

  it("debounces edits, preserves last valid geometry, and retries transport failures", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(clientModule, "previewPairedClipAngle");
    spy.mockResolvedValueOnce(pairedClipAnglePreviewFixture());
    let input: PairedClipAnglePreviewInput = { request: loadPairedClipAngleBenchmark("US_CUSTOMARY"), revision: 0, immediate: true, validationMessage: null };
    const { result, rerender } = renderHook(() => usePairedClipAnglePreview(input));
    await act(async () => { await Promise.resolve(); });
    expect(result.current.state).toBe("CURRENT_VALID");
    spy.mockResolvedValueOnce(pairedClipAnglePreviewFixture("INVALID_GEOMETRY"));
    input = { ...input, request: structuredClone(input.request), revision: 1, immediate: false };
    rerender();
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    expect(result.current.invalidDetail).toBe("Controlled invalid geometry");
    spy.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "offline", null));
    input = { ...input, request: structuredClone(input.request), revision: 2 };
    rerender();
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(result.current.state).toBe("PREVIEW_FAILED_SHOWING_LAST_VALID");
    expect(result.current.error?.message).toBe("offline");
    spy.mockResolvedValueOnce(pairedClipAnglePreviewFixture());
    act(() => { result.current.retry(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(result.current.state).toBe("CURRENT_VALID");
  });

  it("blocks local invalid input without a request and handles unexpected failures", async () => {
    const spy = vi.spyOn(clientModule, "previewPairedClipAngle");
    const invalid: PairedClipAnglePreviewInput = { request: loadPairedClipAngleBenchmark("US_CUSTOMARY"), revision: 1, immediate: false, validationMessage: "invalid" };
    const blocked = renderHook(() => usePairedClipAnglePreview(invalid));
    expect(blocked.result.current.state).toBe("NO_VALID_PREVIEW");
    expect(spy).not.toHaveBeenCalled();
    blocked.unmount();
    spy.mockRejectedValueOnce(new Error("unexpected"));
    const valid = { ...invalid, validationMessage: null, immediate: true };
    const failed = renderHook(() => usePairedClipAnglePreview(valid));
    await waitFor(() => { expect(failed.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(failed.result.current.error?.message).toMatch(/Unexpected paired/iu);
  });

  it("classifies empty invalid reasons, validation transport errors, and local invalidity after success", async () => {
    const spy = vi.spyOn(clientModule, "previewPairedClipAngle");
    const invalid = pairedClipAnglePreviewFixture("INVALID_GEOMETRY");
    invalid.geometry_invalid_reasons = [];
    spy.mockResolvedValueOnce(invalid);
    let input: PairedClipAnglePreviewInput = { request: loadPairedClipAngleBenchmark("US_CUSTOMARY"), revision: 0, immediate: true, validationMessage: null };
    const emptyReason = renderHook(() => usePairedClipAnglePreview(input));
    await waitFor(() => { expect(emptyReason.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(emptyReason.result.current.invalidDetail).toBeNull();
    emptyReason.unmount();

    spy.mockRejectedValueOnce(new EvaluationTransportError("VALIDATION", 422, "invalid", { detail: "bad field" }));
    const validationFailure = renderHook(() => usePairedClipAnglePreview(input));
    await waitFor(() => { expect(validationFailure.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(validationFailure.result.current.invalidDetail).toBe("bad field");
    validationFailure.unmount();

    spy.mockResolvedValueOnce(pairedClipAnglePreviewFixture());
    const local = renderHook(() => usePairedClipAnglePreview(input));
    await waitFor(() => { expect(local.result.current.state).toBe("CURRENT_VALID"); });
    input = { ...input, revision: 1, validationMessage: "local invalid" };
    local.rerender();
    expect(local.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
  });

  it("ignores stale and disposed completions and intentional aborts", async () => {
    const spy = vi.spyOn(clientModule, "previewPairedClipAngle");
    let resolveOld!: (value: ReturnType<typeof pairedClipAnglePreviewFixture>) => void;
    spy.mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve; }));
    spy.mockResolvedValueOnce(pairedClipAnglePreviewFixture());
    let input: PairedClipAnglePreviewInput = { request: loadPairedClipAngleBenchmark("US_CUSTOMARY"), revision: 0, immediate: true, validationMessage: null };
    const latest = renderHook(() => usePairedClipAnglePreview(input));
    input = { ...input, request: structuredClone(input.request), revision: 1 };
    latest.rerender();
    await waitFor(() => { expect(latest.result.current.state).toBe("CURRENT_VALID"); });
    resolveOld(pairedClipAnglePreviewFixture("INVALID_GEOMETRY"));
    await act(async () => { await Promise.resolve(); });
    expect(latest.result.current.state).toBe("CURRENT_VALID");
    latest.unmount();

    let rejectDisposed!: (reason: unknown) => void;
    spy.mockReturnValueOnce(new Promise((_resolve, reject) => { rejectDisposed = reject; }));
    const disposed = renderHook(() => usePairedClipAnglePreview(input));
    disposed.unmount();
    rejectDisposed(new Error("late disposed error"));
    await act(async () => { await Promise.resolve(); });

    spy.mockRejectedValueOnce(new DOMException("aborted", "AbortError"));
    const aborted = renderHook(() => usePairedClipAnglePreview({ ...input, revision: 2 }));
    await act(async () => { await Promise.resolve(); });
    expect(aborted.result.current.state).toBe("PREVIEW_PENDING");
  });
});

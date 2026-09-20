import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  CLIP_ANGLE_DESIGN_PATH,
  CLIP_ANGLE_PREVIEW_PATH,
  EvaluationTransportError,
  evaluateClipAngle,
  previewClipAngle,
} from "../src/api/client";
import * as clientModule from "../src/api/client";
import { loadClipAngleBenchmark } from "../src/fixtures/clipAngleBenchmarks";
import { buildClipAngleSceneModel } from "../src/visualization/clipAngleSceneModel";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import {
  clipAnglePreviewErrorDetail,
  useClipAnglePreview,
  type ClipAnglePreviewInput,
} from "../src/workspace/clipAngleWorkflow";
import {
  clipAngleDesignFixture,
  clipAnglePreviewFixture,
  MATERIAL_AXIS_SUPPORT_MATRIX,
  minimalClipAngleRequest,
  withSupportMaterialGeometry,
} from "./clipAngleFixtures";

const PROFILE_ELEMENTS = {
  FLAT_PLATE: ["PLATE"],
  ANGLE: ["LEG_1", "LEG_2"],
  CHANNEL: ["WEB", "TOP_FLANGE", "BOTTOM_FLANGE"],
  WIDE_FLANGE_I: ["WEB", "TOP_FLANGE", "BOTTOM_FLANGE"],
  RECTANGULAR_HOLLOW_SECTION: [
    "TOP_WALL",
    "BOTTOM_WALL",
    "SIDE_WALL_1",
    "SIDE_WALL_2",
  ],
  SOLID_RECTANGULAR_SECTION: ["PLATE"],
} as const;
const PROFILE_FAMILIES = Object.keys(PROFILE_ELEMENTS) as (keyof typeof PROFILE_ELEMENTS)[];
const PROFILE_MATRIX = (["BRACE", "BEAM"] as const).flatMap((role) =>
  PROFILE_FAMILIES.map((family) => [role, family, PROFILE_ELEMENTS[family]] as const),
);

function withProfileGeometry(
  source: ReturnType<typeof clipAnglePreviewFixture>,
  family: keyof typeof PROFILE_ELEMENTS,
  role: "BRACE" | "BEAM" = "BRACE",
): ReturnType<typeof clipAnglePreviewFixture> {
  const result = structuredClone(source);
  const visualization = result.result.visualization;
  if (visualization === null) throw new Error("Profile fixture requires visualization.");
  const template = visualization.boxes.find(
    (value) => value.owner_id === "clip-angle-connected-member",
  );
  const material = visualization.connected_member_material_regions[0];
  if (template === undefined || material === undefined) {
    throw new Error("Profile fixture requires one physical template region.");
  }
  const elements = PROFILE_ELEMENTS[family];
  visualization.connected_member_role = role;
  visualization.connected_member_profile_family = family;
  visualization.boxes = [
    ...visualization.boxes.filter(
      (value) => value.owner_id !== "clip-angle-connected-member",
    ),
    ...elements.map((element, index) => ({
      ...template,
      id: `MEMBER:clip-angle-connected-member:${element}:${String(index)}`,
      role: element,
      physical_element_id: element,
      material_region_id: `${element}_REGION`,
      center: [
        template.center[0],
        template.center[1],
        { ...template.center[2], value: String(index) },
      ] as const,
    })),
  ];
  visualization.connected_member_material_regions = elements.map((element) => ({
    ...material,
    id: `clip-angle-connected-member:${element}:material-axes`,
    physical_element_id: element,
    material_region_id: `${element}_REGION`,
  }));
  return result;
}


function withTrimmedProfileGeometry(
  source: ReturnType<typeof clipAnglePreviewFixture>,
  family: keyof typeof PROFILE_ELEMENTS,
  role: "BRACE" | "BEAM" = "BRACE",
): ReturnType<typeof clipAnglePreviewFixture> {
  const result = withProfileGeometry(source, family, role);
  const visualization = result.result.visualization;
  if (visualization === null) throw new Error("Trimmed fixture requires visualization.");
  const connected = visualization.boxes.filter(
    (value) => value.owner_id === "clip-angle-connected-member",
  );
  const unit = visualization.bolt_diameter.unit;
  const quantity = (value: number) => ({
    value: String(value),
    unit,
    canonical_value: String(unit === "in" ? value * 25.4 : value),
    canonical_unit: "mm",
  });
  const point = (x: number, y: number, z: number) => (
    [quantity(x), quantity(y), quantity(z)] as const
  );
  const trianglePoints = (offset: number) => {
    const corners = [
      point(-0.5, 1, offset), point(0, 1, offset),
      point(-0.5, 8, offset), point(0, 8, offset),
      point(-0.5, 1, offset + 1), point(0, 1, offset + 1),
      point(-0.5, 8, offset + 1), point(0, 8, offset + 1),
    ] as const;
    const indices = [
      0, 2, 3, 0, 3, 1, 4, 5, 7, 4, 7, 6,
      0, 1, 5, 0, 5, 4, 2, 6, 7, 2, 7, 3,
      0, 4, 6, 0, 6, 2, 1, 3, 7, 1, 7, 5,
    ] as const;
    return indices.map((index) => corners[index]);
  };
  visualization.meshes = connected.map((box, index) => ({
    id: `TRIMMED:MEMBER:clip-angle-connected-member:${box.role}:${String(index)}`,
    owner_id: "clip-angle-connected-member",
    role: box.role,
    physical_element_id: box.physical_element_id ?? box.role,
    material_region_id: box.material_region_id ?? `${box.role}_REGION`,
    points: trianglePoints(index * 2),
  }));
  visualization.trim = {
    ...visualization.trim,
    enabled: true,
    cut_plane_id: "CLIP_ANGLE_CONNECTED_MEMBER_END_CUT_PLANE",
    cut_plane_origin: point(0, 1, 0),
    cut_plane_normal: ["0", "1", "0"],
    measured_plane_clearance: quantity(0.5),
    interference_status: "TRIMMED_CLEAR",
    trimmed_member_geometry_identity: "d".repeat(64),
    fabricated_trim_edge_ids: connected.map((box) => `${box.role}:0:CUT`),
    fabricated_trim_edge_id: `${connected[0]?.role ?? "PLATE"}:0:CUT`,
  };
  return result;
}

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("controlled Stage 3.3A benchmark loader", () => {
  it("loads exact U.S. geometry and independent layouts", () => {
    const request = loadClipAngleBenchmark("US_CUSTOMARY");
    expect(request.connector_dimensions).toEqual({
      connected_leg_width: { value: "4", unit: "in" },
      support_leg_width: { value: "4", unit: "in" },
      thickness: { value: "0.5", unit: "in" },
      connector_length: { value: "8", unit: "in" },
    });
    expect(request.interface_a_layout).toEqual(request.interface_b_layout);
    expect(request.interface_a_layout).not.toBe(request.interface_b_layout);
    expect(request.global_force).toEqual({ x: "0", y: "0", z: "3", unit: "kip" });
    expect(request.global_reference_point).toEqual({ x: "2.25", y: "2.25", z: "0", unit: "in" });
  });

  it("loads the exact equivalent SI fixture and returns fresh objects", () => {
    const request = loadClipAngleBenchmark("SI");
    expect(request.connector_dimensions.connector_length).toEqual({ value: "203.2", unit: "mm" });
    expect(request.hole_diameter).toEqual({ value: "14.3002", unit: "mm" });
    expect(request.global_force.z).toBe("13.3446648457815");
    request.interface_a_layout.pitch.value = "999";
    expect(loadClipAngleBenchmark("SI").interface_a_layout.pitch.value).toBe("50.8");
  });
});

describe("backend-authored clip-angle scene adapter", () => {
  it("renders two legs, support, profile, both independent groups, and material regions", () => {
    const visualization = clipAnglePreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Fixture visualization required.");
    const model = buildClipAngleSceneModel(visualization);

    expect(model.boxes).toHaveLength(6);
    expect(model.boxes.filter((value) => value.ownerId === "single-clip-angle-connector")).toHaveLength(2);
    expect(model.cylinders.filter((value) => value.kind === "BOLT")).toHaveLength(8);
    expect(model.cylinders.filter((value) => value.kind === "HOLE")).toHaveLength(8);
    expect(new Set(model.cylinders.map((value) => value.ownerBoltId)).size).toBe(8);
    expect(model.materialAxes).toHaveLength(6);
    expect(model.materialAxes.every((value) => value.presentation !== null)).toBe(true);
    expect(model.materialAxes.filter(
      (value) => value.componentId === "single-clip-angle-connector",
    ).map((value) => value.elementId)).toEqual([
      "CONNECTED_MEMBER_LEG",
      "SUPPORT_LEG",
    ]);
    expect(model.materialAxes.filter(
      (value) => value.componentId === "clip-angle-connected-member",
    ).map((value) => value.elementId)).toEqual(["PLATE"]);
    expect(model.materialAxes.filter(
      (value) => value.componentId === "clip-angle-support",
    ).map((value) => value.elementId)).toEqual([
      "WEB",
      "TOP_FLANGE",
      "BOTTOM_FLANGE",
    ]);
    expect(model.zones.map((value) => value.interfaceId)).toEqual([
      "CONNECTED_MEMBER_TO_CLIP_ANGLE",
      "CLIP_ANGLE_TO_SUPPORT",
    ]);
    expect(model.frames).toHaveLength(3);
    expect(model.appliedArrows.find((value) => value.component === "FZ")).toMatchObject({
      signedValue: 3,
      sense: "POSITIVE",
      isZero: false,
    });
    expect(model.appliedArrows.find((value) => value.component === "FX")).toMatchObject({
      signedValue: 0,
      sense: "ZERO",
      isZero: true,
    });
    expect(model.boundsRadius).toBeGreaterThan(1);
    expect(model.fitCenter).toEqual(model.boundsCenter);

    const metricNegative = structuredClone(visualization);
    metricNegative.bolt_diameter.unit = "mm";
    metricNegative.global_force.x.value = "-2";
    const alternate = buildClipAngleSceneModel(metricNegative);
    expect(alternate.unitSystem).toBe("SI");
    expect(alternate.appliedArrows.find((value) => value.component === "FX")?.sense).toBe("NEGATIVE");
  });

  it.each(PROFILE_MATRIX)(
    "replaces the complete %s connected-member scene with %s backend primitives",
    (role, family, elements) => {
      const responseValue = withProfileGeometry(
        clipAnglePreviewFixture(),
        family,
        role,
      );
      const visualization = responseValue.result.visualization;
      if (visualization === null) throw new Error("Fixture visualization required.");
      const model = buildClipAngleSceneModel(visualization);
      const connected = model.boxes.filter(
        (value) => value.ownerId === "clip-angle-connected-member",
      );

      expect(connected.map((value) => value.elementId)).toEqual(elements);
      expect(connected.every((value) => value.ownerRole === (role === "BRACE" ? "BRACE" : "OTHER")))
        .toBe(true);
      expect(connected).toHaveLength(elements.length);
      expect(connected.every((value) => value.id !== "clip-angle-connected-member-profile"))
        .toBe(true);
      expect(model.materialAxes.filter(
        (value) => value.componentId === "clip-angle-connected-member",
      )).toHaveLength(elements.length);
    },
  );

  it.each(MATERIAL_AXIS_SUPPORT_MATRIX)(
    "binds every $targetId supporting-member region to backend physical primitives",
    (entry) => {
      const source = clipAnglePreviewFixture().result.visualization;
      if (source === null) throw new Error("Fixture visualization required.");
      const visualization = withSupportMaterialGeometry(source, entry);
      const axes = buildClipAngleSceneModel(visualization).materialAxes.filter(
        (value) => value.componentId === "clip-angle-support",
      );

      expect(axes.map((value) => value.elementId)).toEqual(entry.elements);
      expect(axes.every((value) => value.presentation !== null)).toBe(true);
      expect(axes.some((value) => value.elementId === "CAVITY")).toBe(false);
    },
  );

  it.each(PROFILE_MATRIX)(
    "replaces every %s %s untrimmed region with backend-authored trim meshes",
    (role, family, elements) => {
      const responseValue = withTrimmedProfileGeometry(
        clipAnglePreviewFixture(),
        family,
        role,
      );
      const visualization = responseValue.result.visualization;
      if (visualization === null) throw new Error("Trimmed fixture visualization required.");
      const model = buildClipAngleSceneModel(visualization);
      const connectedBoxes = model.boxes.filter(
        (value) => value.ownerId === "clip-angle-connected-member",
      );
      const connectedMeshes = model.meshes.filter(
        (value) => value.ownerId === "clip-angle-connected-member",
      );

      expect(connectedBoxes).toEqual([]);
      expect(connectedMeshes.map((value) => value.elementId)).toEqual(elements);
      expect(connectedMeshes.every(
        (value) => value.ownerRole === (role === "BRACE" ? "BRACE" : "OTHER"),
      )).toBe(true);
      expect(model.materialAxes.filter(
        (value) => value.componentId === "clip-angle-connected-member",
      ).every((value) => value.presentation !== null)).toBe(true);
      expect(model.boundsRadius).toBeGreaterThan(1);
    },
  );

  it("restores the authoritative untrimmed profile when trim meshes are absent", () => {
    const untrimmed = clipAnglePreviewFixture().result.visualization;
    if (untrimmed === null) throw new Error("Untrimmed fixture visualization required.");
    const trimmedResponse = withTrimmedProfileGeometry(
      clipAnglePreviewFixture(),
      "WIDE_FLANGE_I",
    );
    const trimmed = trimmedResponse.result.visualization;
    if (trimmed === null) throw new Error("Trimmed fixture visualization required.");

    const trimmedModel = buildClipAngleSceneModel(trimmed);
    const untrimmedModel = buildClipAngleSceneModel(untrimmed);
    expect(trimmedModel.boxes.some(
      (value) => value.ownerId === "clip-angle-connected-member",
    )).toBe(false);
    expect(trimmedModel.meshes).toHaveLength(3);
    expect(untrimmedModel.meshes).toEqual([]);
    expect(untrimmedModel.boxes.some(
      (value) => value.ownerId === "clip-angle-connected-member",
    )).toBe(true);
  });

  it("preserves the backend-authored exterior contact side without a frontend offset", () => {
    const visualization = clipAnglePreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Fixture visualization required.");
    const model = buildClipAngleSceneModel(visualization);
    const connectedMember = model.boxes.find(
      (value) => value.ownerId === "clip-angle-connected-member",
    );
    const connectorLeg = model.boxes.find(
      (value) => value.id === "clip-angle-connected-leg-solid",
    );
    if (connectedMember === undefined || connectorLeg === undefined) {
      throw new Error("Contact-side boxes required.");
    }
    const projection = (box: typeof connectedMember): readonly [number, number] => {
      const radius = box.size.x / 2 * Math.abs(box.basis[0].x)
        + box.size.y / 2 * Math.abs(box.basis[1].x)
        + box.size.z / 2 * Math.abs(box.basis[2].x);
      return [box.center.x - radius, box.center.x + radius];
    };
    expect(projection(connectedMember)).toEqual([-0.375, 0]);
    expect(projection(connectorLeg)).toEqual([0, 0.5]);

    const serverMoved = structuredClone(visualization);
    const serverMember = serverMoved.boxes.find(
      (value) => value.owner_id === "clip-angle-connected-member",
    );
    if (serverMember === undefined) throw new Error("Server member box required.");
    serverMember.center[0].value = "-1.1875";
    const moved = buildClipAngleSceneModel(serverMoved).boxes.find(
      (value) => value.ownerId === "clip-angle-connected-member",
    );
    expect(moved?.center.x).toBe(-1.1875);
  });

  it("fails closed on a nonfinite server quantity and tolerates absent contact boxes", () => {
    const responseValue = clipAnglePreviewFixture();
    const visualization = responseValue.result.visualization;
    if (visualization === null) throw new Error("Fixture visualization required.");
    const invalid = structuredClone(visualization);
    invalid.bolt_diameter.value = "NaN";
    expect(() => buildClipAngleSceneModel(invalid)).toThrow("finite quantities");

    const withoutLegs = structuredClone(visualization);
    withoutLegs.boxes = withoutLegs.boxes.filter((value) => !value.id.includes("leg-solid"));
    expect(buildClipAngleSceneModel(withoutLegs).zones).toEqual([]);

    const unclassified = structuredClone(visualization);
    const support = unclassified.boxes.find(
      (value) => value.owner_id === "clip-angle-support",
    );
    if (support === undefined) throw new Error("Fixture support box required.");
    support.owner_id = "unclassified-owner";
    support.role = "UNCLASSIFIED_REGION";
    support.physical_element_id = null;
    support.material_region_id = null;
    expect(buildClipAngleSceneModel(unclassified).boxes.find(
      (value) => value.id === support.id,
    )?.materialRegionId).toBeNull();
  });
});

describe("typed clip-angle API client", () => {
  afterEach(() => { vi.unstubAllGlobals(); });

  it("posts preview and design only to the two exact stateless routes", async () => {
    const preview = clipAnglePreviewFixture();
    const design = clipAngleDesignFixture();
    const fetch = vi.fn().mockResolvedValueOnce(response(preview)).mockResolvedValueOnce(response(design));
    vi.stubGlobal("fetch", fetch);
    const request = minimalClipAngleRequest();
    const signal = new AbortController().signal;
    await expect(previewClipAngle(request, signal)).resolves.toEqual(preview);
    await expect(evaluateClipAngle(request, signal)).resolves.toEqual(design);
    expect(preview.orchestration_contract_version).toBe("3.3C2-RC1");
    expect(preview.result.orchestration_contract_version).toBe("3.3C2-RC1");
    expect(fetch.mock.calls[0]?.[0]).toBe(CLIP_ANGLE_PREVIEW_PATH);
    expect(fetch.mock.calls[1]?.[0]).toBe(CLIP_ANGLE_DESIGN_PATH);
    expect(fetch.mock.calls[0]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify(request),
      credentials: "same-origin",
      signal,
    });
  });

  it.each([
    [422, "VALIDATION"],
    [401, "IDENTITY"],
    [403, "IDENTITY"],
    [500, "HTTP"],
  ] as const)("classifies clip-angle HTTP %i as %s", async (status, kind) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: "controlled" }, status)));
    await expect(previewClipAngle(minimalClipAngleRequest(), new AbortController().signal)).rejects.toMatchObject({ kind, status });
  });

  it("preserves abort, wraps network failure, and tolerates unreadable error JSON", async () => {
    const abort = new DOMException("cancel", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(abort).mockRejectedValueOnce(new Error("offline")));
    await expect(previewClipAngle(minimalClipAngleRequest(), new AbortController().signal)).rejects.toBe(abort);
    await expect(evaluateClipAngle(minimalClipAngleRequest(), new AbortController().signal)).rejects.toMatchObject({ kind: "NETWORK" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not-json", { status: 503 })));
    await expect(evaluateClipAngle(minimalClipAngleRequest(), new AbortController().signal)).rejects.toMatchObject({ kind: "HTTP", detail: null });
  });

  it.each([
    null,
    {},
    { ...clipAnglePreviewFixture(), api_transport_schema_version: "wrong" },
    { ...clipAnglePreviewFixture(), orchestration_contract_version: "3.3C3-RC1" },
    { ...clipAnglePreviewFixture(), preview_schema_version: "wrong" },
    { ...clipAnglePreviewFixture(), geometry_status: "UNKNOWN" },
    { ...clipAnglePreviewFixture(), geometry_invalid_reasons: [1] },
    { ...clipAnglePreviewFixture(), resistance_evaluated: true },
    { ...clipAnglePreviewFixture(), engineering_fingerprint: 2 },
    { ...clipAnglePreviewFixture(), result: null },
  ])("rejects malformed clip-angle preview response %#", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    await expect(previewClipAngle(minimalClipAngleRequest(), new AbortController().signal)).rejects.toMatchObject({ kind: "RESPONSE" });
  });

  it.each([
    null,
    {},
    { ...clipAngleDesignFixture(), api_transport_schema_version: "wrong" },
    { ...clipAngleDesignFixture(), orchestration_contract_version: "3.3C3-RC1" },
    { ...clipAngleDesignFixture(), ordinary_pass_allowed: true },
    { ...clipAngleDesignFixture(), connector_body_status: "PASS" },
    { ...clipAngleDesignFixture(), result_fingerprint: 2 },
    { ...clipAngleDesignFixture(), result: null },
  ])("rejects malformed clip-angle design response %#", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    await expect(evaluateClipAngle(minimalClipAngleRequest(), new AbortController().signal)).rejects.toMatchObject({ kind: "RESPONSE" });
  });
});

const previewFetch = vi.fn();

function workflowInput(
  revision = 1,
  immediate = true,
  validationMessage: string | null = null,
): ClipAnglePreviewInput {
  return {
    request: { ...minimalClipAngleRequest(), request_id: `CLIP-${String(revision)}` },
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

describe("Stage 3.3A live-preview workflow", () => {
  beforeEach(() => {
    previewFetch.mockReset();
    vi.stubGlobal("fetch", previewFetch);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("keeps the last valid preview for invalid and failed current requests", async () => {
    previewFetch.mockResolvedValueOnce(response(clipAnglePreviewFixture())).mockResolvedValueOnce(response(clipAnglePreviewFixture("INVALID_GEOMETRY")));
    const { result, rerender } = renderHook(({ value }) => useClipAnglePreview(value), { initialProps: { value: workflowInput(1) } });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_VALID"); });
    const accepted = result.current.response;
    rerender({ value: workflowInput(2, true, "locally invalid") });
    expect(result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    rerender({ value: workflowInput(2) });
    await waitFor(() => { expect(result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID"); });
    expect(result.current.response).toBe(accepted);
    expect(result.current.outdated).toBe(true);

    previewFetch.mockRejectedValueOnce(new Error("offline"));
    rerender({ value: workflowInput(3) });
    await waitFor(() => { expect(result.current.state).toBe("PREVIEW_FAILED_SHOWING_LAST_VALID"); });
  });

  it("uses explicit geometry status and reasons instead of design status or warnings", async () => {
    const bodyLimited = clipAnglePreviewFixture();
    bodyLimited.warnings = ["SINGLE_CLIP_ANGLE_CONNECTOR_BODY_RESISTANCE_NOT_EVALUATED"];
    bodyLimited.result.warnings = bodyLimited.warnings;
    const supportedFailure = clipAnglePreviewFixture("FAIL");
    const invalid = clipAnglePreviewFixture("INVALID_GEOMETRY");
    invalid.warnings = [
      "SINGLE_CLIP_ANGLE_CONNECTOR_BODY_RESISTANCE_NOT_EVALUATED",
      "CONNECTED_MEMBER_CLIP_ANGLE_INTERFERENCE",
    ];
    invalid.result.warnings = invalid.warnings;
    invalid.geometry_invalid_reasons = ["CONNECTED_MEMBER_CLIP_ANGLE_INTERFERENCE"];
    invalid.result.geometry_invalid_reasons = invalid.geometry_invalid_reasons;
    previewFetch
      .mockResolvedValueOnce(response(bodyLimited))
      .mockResolvedValueOnce(response(supportedFailure))
      .mockResolvedValueOnce(response(invalid));

    const hook = renderHook(({ value }) => useClipAnglePreview(value), {
      initialProps: { value: workflowInput(1) },
    });
    await waitFor(() => { expect(hook.result.current.state).toBe("CURRENT_VALID"); });
    expect(hook.result.current.acceptedRevision).toBe(1);

    hook.rerender({ value: workflowInput(2) });
    await waitFor(() => { expect(hook.result.current.acceptedRevision).toBe(2); });
    expect(hook.result.current.state).toBe("CURRENT_VALID");
    expect(hook.result.current.response?.assembly_status).toBe("FAIL");

    hook.rerender({ value: workflowInput(3) });
    await waitFor(() => {
      expect(hook.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    });
    expect(hook.result.current.acceptedRevision).toBe(2);
    expect(hook.result.current.invalidDetail).toBe("CONNECTED_MEMBER_CLIP_ANGLE_INTERFERENCE");
    expect(hook.result.current.response?.assembly_status).toBe("FAIL");
  });

  it("handles local validation, debounce, abort, latest response, and retry", async () => {
    const { result, unmount } = renderHook(({ value }) => useClipAnglePreview(value), { initialProps: { value: workflowInput(1, true, "incomplete") } });
    expect(result.current.state).toBe("NO_VALID_PREVIEW");
    expect(previewFetch).not.toHaveBeenCalled();
    unmount();

    vi.useFakeTimers();
    previewFetch.mockResolvedValueOnce(response(clipAnglePreviewFixture()));
    const debouncedInput = workflowInput(2, false);
    const debounced = renderHook(() => useClipAnglePreview(debouncedInput));
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(previewFetch).toHaveBeenCalledTimes(1);
    debounced.unmount();
    vi.useRealTimers();

    previewFetch.mockReset();
    const first = deferred<Response>();
    const second = deferred<Response>();
    previewFetch.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const latest = renderHook(({ value }) => useClipAnglePreview(value), { initialProps: { value: workflowInput(3) } });
    const firstCall = previewFetch.mock.calls[0];
    if (firstCall === undefined) throw new Error("Initial clip-angle preview call required.");
    const firstSignal = (firstCall[1] as RequestInit).signal;
    if (firstSignal === undefined || firstSignal === null) {
      throw new Error("Preview abort signal required.");
    }
    const wideFlangeInput = workflowInput(4);
    wideFlangeInput.request.connected_member_profile = {
      ...wideFlangeInput.request.connected_member_profile,
      profile_family: "WIDE_FLANGE_I",
      dimensions: {
        member_length: { value: "8", unit: "in" },
        depth: { value: "8", unit: "in" },
        flange_width: { value: "8", unit: "in" },
        web_thickness: { value: "0.5", unit: "in" },
        flange_thickness: { value: "0.5", unit: "in" },
      },
      selected_profile_surface: "WEB_POS_FACE",
    };
    latest.rerender({ value: wideFlangeInput });
    expect(firstSignal.aborted).toBe(true);
    const latestCall = previewFetch.mock.calls[1];
    const latestInit = latestCall?.[1] as RequestInit | undefined;
    if (typeof latestInit?.body !== "string") {
      throw new Error("Latest profile preview request string body required.");
    }
    expect(JSON.parse(latestInit.body)).toMatchObject({
      connected_member_profile: { profile_family: "WIDE_FLANGE_I" },
    });
    const newest = withTrimmedProfileGeometry(clipAnglePreviewFixture(), "WIDE_FLANGE_I");
    newest.request_id = "newest";
    act(() => { second.resolve(response(newest)); });
    await waitFor(() => { expect(latest.result.current.response?.request_id).toBe("newest"); });
    const currentVisualization = latest.result.current.response?.result.visualization;
    if (currentVisualization === null || currentVisualization === undefined) {
      throw new Error("Newest profile visualization required.");
    }
    expect(buildClipAngleSceneModel(currentVisualization).meshes
      .filter((value) => value.ownerId === "clip-angle-connected-member")
      .map((value) => value.elementId))
      .toEqual(PROFILE_ELEMENTS.WIDE_FLANGE_I);
    expect(buildClipAngleSceneModel(currentVisualization).boxes
      .some((value) => value.ownerId === "clip-angle-connected-member"))
      .toBe(false);
    act(() => { first.resolve(response(clipAnglePreviewFixture())); });
    await act(async () => { await Promise.resolve(); });
    expect(latest.result.current.response?.request_id).toBe("newest");
    expect(latest.result.current.response?.result.visualization
      ?.connected_member_profile_family).toBe("WIDE_FLANGE_I");

    previewFetch.mockResolvedValueOnce(response(clipAnglePreviewFixture()));
    act(() => { latest.result.current.retry(); });
    await waitFor(() => { expect(previewFetch).toHaveBeenCalledTimes(3); });
  });

  it("ignores abort, wraps unexpected error, and preserves validation error detail", async () => {
    previewFetch.mockRejectedValueOnce(new DOMException("cancel", "AbortError"));
    const abortedInput = workflowInput(1);
    const first = renderHook(() => useClipAnglePreview(abortedInput));
    await act(async () => { await Promise.resolve(); });
    expect(first.result.current.state).toBe("PREVIEW_PENDING");
    first.unmount();

    const rawFailure = vi.spyOn(clientModule, "previewClipAngle").mockRejectedValueOnce(
      new Error("unexpected"),
    );
    const unexpectedInput = workflowInput(2);
    const unexpected = renderHook(() => useClipAnglePreview(unexpectedInput));
    await waitFor(() => { expect(unexpected.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(unexpected.result.current.error).toBeInstanceOf(EvaluationTransportError);
    rawFailure.mockRestore();

    previewFetch.mockResolvedValueOnce(response({ detail: { message: "Exact server reason." } }, 422));
    const validationInput = workflowInput(3);
    const validation = renderHook(() => useClipAnglePreview(validationInput));
    await waitFor(() => { expect(validation.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(validation.result.current.error).toBeInstanceOf(EvaluationTransportError);
    expect(validation.result.current.invalidDetail).toBe("Exact server reason.");

    const invalidWithoutWarning = clipAnglePreviewFixture("INVALID_GEOMETRY");
    invalidWithoutWarning.warnings = [];
    invalidWithoutWarning.result.warnings = [];
    invalidWithoutWarning.geometry_invalid_reasons = [];
    invalidWithoutWarning.result.geometry_invalid_reasons = [];
    previewFetch.mockResolvedValueOnce(response(invalidWithoutWarning));
    const emptyWarningInput = workflowInput(4);
    const emptyWarning = renderHook(() => useClipAnglePreview(emptyWarningInput));
    await waitFor(() => { expect(emptyWarning.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(emptyWarning.result.current.invalidDetail).toBeNull();
  });

  it("extracts all controlled validation-detail forms", () => {
    const error = (detail: unknown) => new EvaluationTransportError("VALIDATION", 422, "generic", { detail });
    expect(clipAnglePreviewErrorDetail(error("Direct"))).toBe("Direct");
    expect(clipAnglePreviewErrorDetail(error({ message: "Object" }))).toBe("Object");
    expect(clipAnglePreviewErrorDetail(error([null, { msg: "Field", loc: ["body", 0, "rows"] }]))).toBe("body → 0 → rows: Field");
    expect(clipAnglePreviewErrorDetail(error([{ msg: "Bare" }]))).toBe("Bare");
    expect(clipAnglePreviewErrorDetail(error([{ loc: ["body"] }]))).toBeNull();
    expect(clipAnglePreviewErrorDetail(error(1))).toBeNull();
    expect(clipAnglePreviewErrorDetail(null)).toBeNull();
  });
});

import { describe, expect, it } from "vitest";

import {
  SCENE_VIEWS,
  buildMultiRowSceneModel,
  buildSingleBoltSceneModel,
  buildTeeSceneModel,
  calculateCameraClippingPlanes,
  calculateOrthographicZoom,
  calculatePerspectiveDistance,
  calculatePresentationBounds,
  canonicalCylinderRadius,
  materialRegionLabel,
} from "../src/visualization/sceneModel";
import {
  SCHEMATIC_HEAD_ACROSS_FLATS_RATIO,
  SCHEMATIC_HEAD_HEIGHT_RATIO,
  SCHEMATIC_NUT_ACROSS_FLATS_RATIO,
  SCHEMATIC_NUT_THICKNESS_RATIO,
  buildFastenerPresentations,
} from "../src/visualization/fastenerPresentation";
import type { MultiRowVisualization } from "../src/api/multirowContracts";
import { visualizationFixture } from "./fixtures";
import { teeVisualizationFixture } from "./teeFixtures";

function requiredAt<Item>(values: readonly Item[], index: number): Item {
  const value = values[index];
  if (value === undefined) throw new Error(`Missing test item ${String(index)}.`);
  return value;
}

describe("pure visualization snapshot to presentation scene mapping", () => {
  it("maps exact primitives without changing positions, sizes, directions, or statuses", () => {
    const snapshot = visualizationFixture();
    snapshot.components = [
      { id: "member-a", label: "FRP angle brace", participant_kind: "MEMBER", material_kind: "PULTRUDED_FRP", section_family: "ANGLE", frame_id: "MEMBER_LOCAL:member-a", connected_end: "START", elements: [], deferred_primitive_ids: [] },
      { id: "member-b", label: "FRP W column", participant_kind: "MEMBER", material_kind: "PULTRUDED_FRP", section_family: "WIDE_FLANGE", frame_id: "MEMBER_LOCAL:member-b", connected_end: "START", elements: [], deferred_primitive_ids: [] },
    ];
    const deferred = snapshot.primitives[1];
    if (deferred === undefined) throw new Error("Deferred fixture primitive is required.");
    deferred.owner_id = "member-b";
    const model = buildSingleBoltSceneModel(snapshot);
    expect(model.snapshotVersion).toBe("1.3.0-draft");
    expect(model.unitSystem).toBe("US_CUSTOMARY");
    expect(model.lengthUnit).toBe("in");
    expect(model.boxes).toHaveLength(2);
    expect(model.boxes[0]).toMatchObject({
      id: "member-a:LEG_1",
      ownerId: "member-a",
      center: { x: 2, y: 0, z: -0.1875 },
      size: { x: 4, y: 3, z: 0.375 },
      deferred: false,
      ownerLabel: "FRP angle brace",
      ownerRole: "BRACE",
    });
    expect(model.boxes[1]).toMatchObject({ deferred: true, ownerRole: "COLUMN" });
    expect(model.cylinders).toEqual([
      expect.objectContaining({ kind: "BOLT", diameter: 0.5, hardwareLocation: null }),
      expect.objectContaining({ kind: "HOLE", diameter: 0.563, hardwareLocation: null }),
      expect.objectContaining({ kind: "WASHER", diameter: 1, hardwareLocation: "UNDER_HEAD" }),
      expect.objectContaining({ kind: "WASHER", diameter: 1, hardwareLocation: "UNDER_NUT" }),
    ]);
    expect(model.zones[0]).toMatchObject({
      id: "first-zone",
      side: "FIRST",
      patchId: "patch-a",
      selectedContact: false,
    });
    expect(model.zones[0]?.corners).toHaveLength(4);
    expect(model.zones[1]).toMatchObject({
      participantId: "member-b",
      patchId: "patch-b",
      selectedContact: true,
    });
    expect(model.connectionOrientation).toMatchObject({
      connectionSide: "EXTERIOR",
      connectedLeg: "LEG_1",
      outstandingLegSide: "POSITIVE_INTERFACE_Z",
      selectedFlangeSurfaceId: "patch-b",
      selectedContactNormal: { x: -1, y: 0, z: 0 },
      braceToColumnDirectedAngleDegrees: 45,
      planAngleDegrees: 0,
      geometryValid: true,
    });
  });

  it("maps server frame inspection rather than recomputing engineering validity", () => {
    const model = buildSingleBoltSceneModel(visualizationFixture());
    expect(model.frames.find((value) => value.id === "GLOBAL")?.valid).toBe(true);
    expect(model.frames.find((value) => value.ownerId === "member-b")?.valid).toBe(false);
    expect(model.frames.map((value) => value.origin)).toContainEqual({ x: 2, y: 0.1875, z: 0 });
  });

  it("preserves the explicit-geometry snapshot path without template orientation", () => {
    const snapshot = visualizationFixture();
    snapshot.connection_orientation = null;
    const model = buildSingleBoltSceneModel(snapshot);
    expect(model.connectionOrientation).toBeNull();
    expect(model.zones.every((value) => !value.selectedContact)).toBe(true);
  });

  it("maps only exact material triads and retains exact LW/CW/TT vectors", () => {
    const model = buildSingleBoltSceneModel(visualizationFixture());
    expect(model.materialAxes).toHaveLength(1);
    expect(model.materialAxes[0]).toMatchObject({
      componentId: "member-a",
      elementId: "LEG_1",
      lengthwise: { x: 1, y: 0, z: 0 },
      crosswise: { x: 0, y: 1, z: 0 },
      throughThickness: { x: 0, y: 0, z: 1 },
    });
  });

  it("maps every R14B region triad verbatim with physical-owner labels and stable IDs", () => {
    const snapshot = visualizationFixture();
    const cases = [
      ["w", "Supporting W", "WIDE_FLANGE", "WEB", "Web", "W — Web", [0, 0, 1], [-1, 0, 0], [0, -1, 0]],
      ["w", "Supporting W", "WIDE_FLANGE", "TOP_FLANGE", "Top flange", "W — Positive flange", [0, 0, 1], [0, -1, 0], [1, 0, 0]],
      ["w", "Supporting W", "WIDE_FLANGE", "BOTTOM_FLANGE", "Bottom flange", "W — Negative flange", [0, 0, 1], [0, -1, 0], [1, 0, 0]],
      ["i", "Supporting I", "I_SECTION", "WEB", "Web", "I — Web", [0, 0, 1], [-1, 0, 0], [0, -1, 0]],
      ["tee", "Tee connector", "TEE", "STEM", "Stem", "Tee — Stem", [0, 0, 1], [1, 0, 0], [0, 1, 0]],
      ["tee", "Tee connector", "TEE", "FLANGE", "Flange", "Tee — Flange", [0, 0, 1], [0, 1, 0], [-1, 0, 0]],
      ["angle", "Angle brace", "ANGLE", "LEG_1", "Leg 1", "Angle — Leg 1", [1, 0, 0], [0, 0, -1], [0, 1, 0]],
      ["angle", "Angle brace", "ANGLE", "LEG_2", "Leg 2", "Angle — Leg 2", [1, 0, 0], [0, -1, 0], [0, 0, -1]],
      ["channel", "Channel brace", "CHANNEL", "WEB", "Web", "Channel — Web", [1, 0, 0], [0, 0, -1], [0, 1, 0]],
      ["channel", "Channel brace", "CHANNEL", "TOP_FLANGE", "Top flange", "Channel — Positive flange", [1, 0, 0], [0, 1, 0], [0, 0, 1]],
      ["channel", "Channel brace", "CHANNEL", "BOTTOM_FLANGE", "Bottom flange", "Channel — Negative flange", [1, 0, 0], [0, 1, 0], [0, 0, 1]],
      ["rhs", "RHS brace", "RECTANGULAR_TUBE", "TOP_WALL", "Top wall", "RHS — Top wall", [1, 0, 0], [0, -1, 0], [0, 0, -1]],
      ["rhs", "RHS brace", "RECTANGULAR_TUBE", "BOTTOM_WALL", "Bottom wall", "RHS — Bottom wall", [1, 0, 0], [0, -1, 0], [0, 0, -1]],
      ["rhs", "RHS brace", "RECTANGULAR_TUBE", "SIDE_WALL_1", "Side wall 1", "RHS — Side wall 1", [1, 0, 0], [0, 0, 1], [0, -1, 0]],
      ["rhs", "RHS brace", "RECTANGULAR_TUBE", "SIDE_WALL_2", "Side wall 2", "RHS — Side wall 2", [1, 0, 0], [0, 0, 1], [0, -1, 0]],
      ["plate", "Flat plate brace", "PLATE", "PLATE", "Plate", "Flat Plate", [1, 0, 0], [0, 0, -1], [0, 1, 0]],
      ["flat-profile", "Flat plate profile", "FLAT_PLATE", "PLATE", "Plate", "Flat Plate", [1, 0, 0], [0, 0, -1], [0, 1, 0]],
    ] as const;
    const componentCases = new Map(cases.map((item) => [item[0], item]));
    snapshot.components = [...componentCases.values()].map((item) => ({
      id: item[0],
      label: item[1],
      participant_kind: item[0] === "tee" ? "CONNECTOR_COMPONENT" : "MEMBER",
      material_kind: "PULTRUDED_FRP",
      section_family: item[2],
      frame_id: `${item[0] === "tee" ? "CONNECTOR" : "MEMBER"}_LOCAL:${item[0]}`,
      connected_end: item[0] === "tee" ? null : "START",
      elements: cases.filter((candidate) => candidate[0] === item[0]).map((candidate) => ({
        id: candidate[3],
        label: candidate[4],
        role: candidate[3],
        material_region_id: candidate[3],
        primitive_ids: [],
      })),
      deferred_primitive_ids: [],
    }));
    const direction = (values: readonly [number, number, number]) => ({
      x: String(values[0]),
      y: String(values[1]),
      z: String(values[2]),
    });
    snapshot.material_directions = cases.map((item) => ({
      id: `${item[0]}:${item[3]}:material-axes`,
      component_id: item[0],
      physical_element_id: item[3],
      material_region_id: item[3],
      origin: { x: "0", y: "0", z: "0", unit: "in" },
      lengthwise: direction(item[6]),
      crosswise: direction(item[7]),
      through_thickness: direction(item[8]),
      resolution_status: "EXACT",
      reason: null,
    }));
    const canonicalInput = JSON.stringify(snapshot);
    const model = buildSingleBoltSceneModel(snapshot);

    expect(JSON.stringify(snapshot)).toBe(canonicalInput);
    expect(model.materialAxes).toHaveLength(cases.length);
    for (const item of cases) {
      const axes = model.materialAxes.find(
        (candidate) => candidate.componentId === item[0] && candidate.elementId === item[3],
      );
      expect(axes).toBeDefined();
      expect(axes).toMatchObject({
        componentLabel: item[1],
        sectionFamily: item[2],
        elementLabel: item[4],
        materialRegionId: item[3],
        lengthwise: { x: item[6][0], y: item[6][1], z: item[6][2] },
        crosswise: { x: item[7][0], y: item[7][1], z: item[7][2] },
        throughThickness: { x: item[8][0], y: item[8][1], z: item[8][2] },
      });
      if (axes !== undefined) expect(materialRegionLabel(axes)).toBe(item[5]);
    }
    expect(
      materialRegionLabel({
        ...requiredAt(model.materialAxes, 0),
        sectionFamily: "FUTURE_PROFILE",
        elementId: "FUTURE_REGION",
        componentLabel: "Future profile",
        elementLabel: "Future region",
      }),
    ).toBe("Future profile — Future region");
    expect(model.frames.some((frame) => frame.kind === "MEMBER_LOCAL")).toBe(true);
  });

  it("embeds one bounded presentation on every W/I, Channel, Angle, Tee, RHS, and plate region", () => {
    const snapshot = visualizationFixture();
    const cases = [
      ["w", "WIDE_FLANGE", "TOP_FLANGE", [0, 0, 1], [0, -1, 0], [1, 0, 0]],
      ["w", "WIDE_FLANGE", "WEB", [0, 0, 1], [-1, 0, 0], [0, -1, 0]],
      ["w", "WIDE_FLANGE", "BOTTOM_FLANGE", [0, 0, 1], [0, -1, 0], [1, 0, 0]],
      ["i", "I_SECTION", "TOP_FLANGE", [0, 0, 1], [0, -1, 0], [1, 0, 0]],
      ["i", "I_SECTION", "WEB", [0, 0, 1], [-1, 0, 0], [0, -1, 0]],
      ["i", "I_SECTION", "BOTTOM_FLANGE", [0, 0, 1], [0, -1, 0], [1, 0, 0]],
      ["channel", "CHANNEL", "TOP_FLANGE", [1, 0, 0], [0, 1, 0], [0, 0, 1]],
      ["channel", "CHANNEL", "WEB", [1, 0, 0], [0, 0, -1], [0, 1, 0]],
      ["channel", "CHANNEL", "BOTTOM_FLANGE", [1, 0, 0], [0, 1, 0], [0, 0, 1]],
      ["angle", "ANGLE", "LEG_1", [1, 0, 0], [0, 0, -1], [0, 1, 0]],
      ["angle", "ANGLE", "LEG_2", [1, 0, 0], [0, -1, 0], [0, 0, -1]],
      ["tee", "TEE", "FLANGE", [0, 0, 1], [0, 1, 0], [-1, 0, 0]],
      ["tee", "TEE", "STEM", [0, 0, 1], [1, 0, 0], [0, 1, 0]],
      ["rhs", "RECTANGULAR_TUBE", "TOP_WALL", [1, 0, 0], [0, -1, 0], [0, 0, -1]],
      ["rhs", "RECTANGULAR_TUBE", "BOTTOM_WALL", [1, 0, 0], [0, -1, 0], [0, 0, -1]],
      ["rhs", "RECTANGULAR_TUBE", "SIDE_WALL_1", [1, 0, 0], [0, 0, 1], [0, -1, 0]],
      ["rhs", "RECTANGULAR_TUBE", "SIDE_WALL_2", [1, 0, 0], [0, 0, 1], [0, -1, 0]],
      ["plate", "FLAT_PLATE", "PLATE", [1, 0, 0], [0, 0, -1], [0, 1, 0]],
    ] as const;
    const vectorDto = (value: readonly [number, number, number]) => ({
      x: String(value[0]),
      y: String(value[1]),
      z: String(value[2]),
    });
    const pointDto = (value: readonly [number, number, number]) => ({
      ...vectorDto(value),
      unit: "in",
    });
    const components = new Map(cases.map((value) => [value[0], value[1]]));
    snapshot.components = [...components].map(([id, family]) => ({
      id,
      label: id === "tee" ? "Tee connector" : `${family} profile`,
      participant_kind: id === "tee" ? "CONNECTOR_COMPONENT" : "MEMBER",
      material_kind: "PULTRUDED_FRP",
      section_family: family,
      frame_id: `${id === "tee" ? "CONNECTOR" : "MEMBER"}_LOCAL:${id}`,
      connected_end: id === "tee" ? null : "START",
      elements: cases.filter((value) => value[0] === id).map((value) => ({
        id: value[2],
        label: value[2],
        role: value[2],
        material_region_id: value[2],
        primitive_ids: [`${id}:${value[2]}`],
      })),
      deferred_primitive_ids: [],
    }));
    snapshot.primitives = cases.map((value, index) => ({
      id: `${value[0]}:${value[2]}`,
      label: `${value[0]} ${value[2]}`,
      kind: "BOX",
      owner_id: value[0],
      frame_id: `${value[0]}:frame`,
      physical_element_id: value[2],
      material_region_id: value[2],
      center: pointDto([index * 20, index * 7, index * 3]),
      x_axis: vectorDto(value[3]),
      y_axis: vectorDto(value[4]),
      z_axis: vectorDto(value[5]),
      parameters: [
        { name: "x_start", value: "0" },
        { name: "x_end", value: "12" },
        { name: "min_y", value: "-2" },
        { name: "max_y", value: "2" },
        { name: "min_z", value: "-0.25" },
        { name: "max_z", value: "0.25" },
      ],
      points: [],
      resolution_status: "EXACT",
    }));
    snapshot.view_extension_primitives = [];
    snapshot.material_directions = cases.map((value) => ({
      id: `${value[0]}:${value[2]}:material-axes`,
      component_id: value[0],
      physical_element_id: value[2],
      material_region_id: value[2],
      origin: pointDto([0, 0, 0]),
      lengthwise: vectorDto(value[3]),
      crosswise: vectorDto(value[4]),
      through_thickness: vectorDto(value[5]),
      resolution_status: "EXACT",
      reason: null,
    }));
    const canonicalInput = JSON.stringify(snapshot);
    const model = buildSingleBoltSceneModel(snapshot);

    expect(JSON.stringify(snapshot)).toBe(canonicalInput);
    expect(model.materialAxes).toHaveLength(cases.length);
    expect(model.materialAxes.filter((value) => value.sectionFamily === "WIDE_FLANGE")).toHaveLength(3);
    expect(model.materialAxes.filter((value) => value.sectionFamily === "I_SECTION")).toHaveLength(3);
    expect(model.materialAxes.filter((value) => value.sectionFamily === "CHANNEL")).toHaveLength(3);
    expect(model.materialAxes.filter((value) => value.sectionFamily === "ANGLE")).toHaveLength(2);
    expect(model.materialAxes.filter((value) => value.sectionFamily === "TEE")).toHaveLength(2);
    expect(model.materialAxes.filter((value) => value.sectionFamily === "RECTANGULAR_TUBE")).toHaveLength(4);
    expect(model.materialAxes.filter((value) => value.sectionFamily === "FLAT_PLATE")).toHaveLength(1);
    const origins = new Set<string>();
    for (const axes of model.materialAxes) {
      const primitive = model.boxes.find(
        (value) => value.ownerId === axes.componentId && value.elementId === axes.elementId,
      );
      expect(primitive).toBeDefined();
      expect(axes.origin).toEqual({ x: 0, y: 0, z: 0 });
      expect(axes.presentation).not.toBeNull();
      if (primitive === undefined || axes.presentation === null) continue;
      expect(axes.presentation.primitiveIds).toEqual([primitive.id]);
      expect(axes.presentation.lengthwiseLength).toBeGreaterThan(0);
      expect(axes.presentation.crosswiseLength).toBeGreaterThan(0);
      expect(axes.presentation.lengthwiseLength).toBeLessThanOrEqual(4 * 0.72);
      expect(axes.presentation.crosswiseLength).toBeLessThanOrEqual(4 * 0.72);
      const displacement = {
        x: axes.presentation.origin.x - primitive.center.x,
        y: axes.presentation.origin.y - primitive.center.y,
        z: axes.presentation.origin.z - primitive.center.z,
      };
      const projection = (direction: { readonly x: number; readonly y: number; readonly z: number }) =>
        displacement.x * direction.x + displacement.y * direction.y + displacement.z * direction.z;
      expect(projection(axes.lengthwise)).toBeCloseTo(0, 12);
      expect(projection(axes.crosswise)).toBeCloseTo(0, 12);
      expect(projection(axes.throughThickness)).toBeCloseTo(
        0.25 + axes.presentation.surfaceOffset,
        12,
      );
      origins.add(JSON.stringify(axes.presentation.origin));
    }
    expect(origins.size).toBe(cases.length);
  });

  it("maps reference markers, positive directions, negative reversal, and zero flags", () => {
    const model = buildSingleBoltSceneModel(visualizationFixture());
    expect(model.markers.map((value) => value.memberEnd)).toContain("START");
    expect(model.markers.map((value) => value.memberEnd)).toContain("END");
    expect(model.positiveArrows).toHaveLength(6);
    expect(model.positiveArrows[0]).toMatchObject({ signedValue: null, axis: { x: 1, y: 0, z: 0 } });
    expect(model.appliedArrows[0]).toMatchObject({
      signedValue: -0.7,
      sense: "NEGATIVE",
      axis: { x: -1, y: 0, z: 0 },
      axialLoadingSense: "TENSION",
    });
    expect(model.appliedArrows.filter((value) => value.isZero)).toHaveLength(3);
    expect(model.appliedArrows.find((value) => value.component === "MZ")?.kind).toBe("ROTATIONAL");
  });

  it("defines unambiguous global camera directions including exact opposing side views", () => {
    expect(Object.keys(SCENE_VIEWS)).toEqual(["3D", "Front", "Top", "Side 1", "Side 2"]);
    expect(SCENE_VIEWS.Front).toMatchObject({
      cameraDirection: { x: 0, y: -1, z: 0 },
      up: { x: 0, y: 0, z: 1 },
      orthographic: true,
    });
    expect(SCENE_VIEWS.Top.cameraDirection).toEqual({ x: 0, y: 0, z: 1 });
    expect(SCENE_VIEWS["Side 1"]).toMatchObject({
      cameraDirection: { x: 1, y: 0, z: 0 },
      up: { x: 0, y: 0, z: 1 },
      orthographic: true,
    });
    expect(SCENE_VIEWS["Side 2"]).toMatchObject({
      cameraDirection: { x: -1, y: 0, z: 0 },
      up: SCENE_VIEWS["Side 1"].up,
      orthographic: true,
    });
    expect(SCENE_VIEWS["3D"].orthographic).toBe(false);
  });

  it("maps independent canonical bolt and hole diameters to exact model-space radii", () => {
    const baselineSnapshot = visualizationFixture();
    const baseline = buildSingleBoltSceneModel(baselineSnapshot);
    const changedSnapshot = visualizationFixture();
    changedSnapshot.bolt.bolt_diameter = "0.75";
    requiredAt(changedSnapshot.bolt.holes, 0).diameter = "0.875";
    const changed = buildSingleBoltSceneModel(changedSnapshot);

    expect(canonicalCylinderRadius(0.5)).toBe(0.25);
    expect(canonicalCylinderRadius(0.75)).toBe(0.375);
    expect(baseline.cylinders.find((value) => value.kind === "BOLT")?.diameter).toBe(0.5);
    expect(changed.cylinders.find((value) => value.kind === "BOLT")?.diameter).toBe(0.75);
    expect(baseline.cylinders.find((value) => value.kind === "HOLE")?.diameter).toBe(0.563);
    expect(changed.cylinders.find((value) => value.kind === "HOLE")?.diameter).toBe(0.875);
  });

  it("calculates presentation-only camera-fit bounds including the empty fallback", () => {
    expect(calculatePresentationBounds([])).toEqual({ center: { x: 0, y: 0, z: 0 }, radius: 1 });
    expect(calculatePresentationBounds([{ x: -2, y: 0, z: 0 }, { x: 2, y: 0, z: 0 }])).toEqual({
      center: { x: 0, y: 0, z: 0 },
      radius: 2,
    });
    const model = buildSingleBoltSceneModel(visualizationFixture());
    expect(model.boundsRadius).toBeGreaterThan(1);
    expect(model.fitCenter).toEqual({ x: 2, y: 0.1875, z: 0 });
    expect(model.fitRadius).toBeGreaterThanOrEqual(model.boundsRadius);
  });

  it("replaces targetable member solids with backend-authored view extensions for camera fit", () => {
    const baseline = buildSingleBoltSceneModel(visualizationFixture());
    const snapshot = visualizationFixture();
    const engineeringBrace = requiredAt(snapshot.primitives, 0);
    if (engineeringBrace.center === null) throw new Error("Brace center fixture is required.");
    snapshot.view_extension_primitives = [
      {
        ...structuredClone(engineeringBrace),
        id: "view:member-a:LEG_1",
        label: "Angle leg 1 view extension",
        center: { ...engineeringBrace.center, x: "4" },
        parameters: engineeringBrace.parameters.map((parameter) =>
          parameter.name === "x_end" ? { ...parameter, value: "8" } : parameter,
        ),
      },
    ];

    const extended = buildSingleBoltSceneModel(snapshot);
    const braceBoxes = extended.boxes.filter((value) => value.ownerId === "member-a");
    expect(braceBoxes).toHaveLength(1);
    expect(braceBoxes[0]).toMatchObject({ id: "view:member-a:LEG_1", size: { x: 8 } });
    expect(extended.fitCenter).toEqual(baseline.fitCenter);
    expect(extended.fitRadius).toBeGreaterThan(baseline.fitRadius);
  });

  it("fits orthographic cameras independently of physical unit scale", () => {
    expect(calculateOrthographicZoom(700, 5)).toBeCloseTo(50);
    expect(calculateOrthographicZoom(700, 127)).toBeCloseTo(50 / 25.4);
    expect(calculateOrthographicZoom(700, 0)).toBeCloseTo(250);
  });

  it("fits perspective cameras to the same presentation fraction independent of units", () => {
    expect(calculatePerspectiveDistance(5, 40)).toBeCloseTo(19.474, 2);
    expect(calculatePerspectiveDistance(127, 40) / 25.4).toBeCloseTo(
      calculatePerspectiveDistance(5, 40),
    );
    expect(calculatePerspectiveDistance(0, 40)).toBeGreaterThan(3);
  });

  it("scales camera clipping planes with the fitted physical-unit profile", () => {
    const us = calculateCameraClippingPlanes(20, 5);
    const si = calculateCameraClippingPlanes(20 * 25.4, 5 * 25.4);
    expect(si.near / 25.4).toBeCloseTo(us.near);
    expect(si.far / 25.4).toBeCloseTo(us.far);
    expect(calculateCameraClippingPlanes(4, 0)).toEqual({ near: 0.001, far: 104 });
  });

  it("rejects blank and non-finite decimal transport values", () => {
    const blank = visualizationFixture();
    blank.bolt.bolt_diameter = " ";
    expect(() => buildSingleBoltSceneModel(blank)).toThrow("must be a decimal string");
    const infinite = visualizationFixture();
    requiredAt(infinite.frames, 0).frame.origin.x = "Infinity";
    expect(() => buildSingleBoltSceneModel(infinite)).toThrow("must be finite");
  });

  it("rejects boxes without canonical placement or required primitive parameters", () => {
    const missingPlacement = visualizationFixture();
    requiredAt(missingPlacement.primitives, 0).center = null;
    expect(() => buildSingleBoltSceneModel(missingPlacement)).toThrow("lacks canonical placement");
    const missingParameter = visualizationFixture();
    const firstPrimitive = requiredAt(missingParameter.primitives, 0);
    firstPrimitive.parameters = firstPrimitive.parameters.filter(
      (value) => value.name !== "max_z",
    );
    expect(() => buildSingleBoltSceneModel(missingParameter)).toThrow("lacks max_z");
  });

  it("rejects incomplete triangle meshes", () => {
    const snapshot = visualizationFixture();
    const template = requiredAt(snapshot.primitives, 0);
    snapshot.primitives.push({
      ...structuredClone(template),
      id: "incomplete-mesh",
      kind: "TRIANGLE_MESH",
      center: null,
      x_axis: null,
      y_axis: null,
      z_axis: null,
      parameters: [],
      points: [
        { x: "0", y: "0", z: "0", unit: "in" },
        { x: "1", y: "0", z: "0", unit: "in" },
      ],
    });

    expect(() => buildSingleBoltSceneModel(snapshot)).toThrow(
      "Triangle mesh incomplete-mesh must contain complete triangles.",
    );
  });

  it("rejects action arrows whose canonical reference point is absent", () => {
    const snapshot = visualizationFixture();
    snapshot.reference_points = snapshot.reference_points.filter(
      (value) => value.id !== "action:action-1:reference",
    );
    expect(() => buildSingleBoltSceneModel(snapshot)).toThrow(
      "Action direction lacks reference action:action-1:reference",
    );
  });

  it("requires backend-authored physical geometry and bolt placements for multi-row scenes", () => {
    expect(() => buildMultiRowSceneModel({} as MultiRowVisualization)).toThrow(
      "lacks canonical physical connection geometry",
    );
    expect(() => buildMultiRowSceneModel({
      physical_connection: visualizationFixture(),
      physical_bolts: [],
    } as unknown as MultiRowVisualization)).toThrow("lacks canonical physical bolt placements");
  });

  it("maps backend-authored multi-row bolts and the external connection-demand resultant", () => {
    const physical = visualizationFixture();
    const meshTemplate = requiredAt(physical.primitives, 0);
    physical.primitives.push({
      ...structuredClone(meshTemplate),
      id: "multi-row-fabricated-mesh",
      kind: "TRIANGLE_MESH",
      center: null,
      x_axis: null,
      y_axis: null,
      z_axis: null,
      parameters: [],
      points: [
        { x: "8", y: "0", z: "0", unit: "in" },
        { x: "9", y: "0", z: "0", unit: "in" },
        { x: "8", y: "1", z: "0", unit: "in" },
      ],
    });
    const first = structuredClone(physical.bolt);
    first.bolt_location_id = "custom-bolt";
    const second = structuredClone(physical.bolt);
    second.bolt_location_id = "B_R2_L1";
    second.center = { ...second.center, y: "4" };
    const snapshot = {
      physical_connection: physical,
      physical_bolts: [
        {
          bolt_id: "custom-bolt",
          row_id: "ROW_1",
          bolt_line_id: "BOLT_LINE_1",
          penetrated_layer_ids: ["layer-A", "layer-B"],
          display: first,
        },
        {
          bolt_id: "B_R2_L1",
          row_id: "ROW_2",
          bolt_line_id: "BOLT_LINE_1",
          penetrated_layer_ids: ["layer-A", "layer-B"],
          display: second,
        },
      ],
      connection_demand: {
        reference_point_id: "CONNECTION_DEMAND",
        origin: physical.bolt.center,
        axis: physical.bolt.axis,
        resultant: { value: "1.25", unit: "kip" },
        frame_id: "BOLT_GROUP_LOCAL:bolt-group-1",
      },
      automatic_bolt_demands: [],
    } as unknown as MultiRowVisualization;

    const model = buildMultiRowSceneModel(snapshot);
    const physicalBolts = model.cylinders.filter((value) => value.kind === "BOLT");
    const physicalHoles = model.cylinders.filter((value) => value.kind === "HOLE");
    expect(physicalBolts).toHaveLength(2);
    expect(physicalBolts.every((value) => value.diameter === 0.5)).toBe(true);
    expect(physicalHoles).toHaveLength(2);
    expect(physicalHoles.every((value) => value.diameter === 0.563)).toBe(true);
    expect(model.markers.find((value) => value.id === "custom-bolt")?.label).toBe("Selected bolt");
    expect(model.markers.find((value) => value.id === "B_R2_L1")?.label).toContain("Row 2");
    expect(model.fitCenter).toEqual(model.markers.find((value) => value.id === "custom-bolt")?.position);
    expect(model.connectionDemandArrows).toEqual([
      expect.objectContaining({
        id: "CONNECTION_DEMAND",
        signedValue: 1.25,
        unit: "kip",
        frameId: "BOLT_GROUP_LOCAL:bolt-group-1",
      }),
    ]);
    expect(model.meshes).toHaveLength(1);
    expect(model.boundsRadius).toBeGreaterThan(4);

    const withoutDemand = buildMultiRowSceneModel({
      ...snapshot,
      connection_demand: null,
    });
    expect(withoutDemand.connectionDemandArrows).toEqual([]);
  });
});

describe("Stage 3.2 Tee canonical scene mapping", () => {
  it("maps backend-authored fabricated trim meshes and removes the untrimmed brace box", () => {
    const snapshot = teeVisualizationFixture();
    const template = snapshot.base_connection.primitives[0];
    if (template === undefined) throw new Error("A primitive fixture is required.");
    snapshot.base_connection.components.push({
      id: snapshot.connected_member_profile.member_id,
      label: "Fabricated FRP angle brace",
      participant_kind: "MEMBER",
      material_kind: "PULTRUDED_FRP",
      section_family: "ANGLE",
      frame_id: "MEMBER_LOCAL:member-a",
      connected_end: "START",
      elements: [],
      deferred_primitive_ids: [],
    });
    snapshot.base_connection.components.push({
      id: "member-b",
      label: "FRP W column",
      participant_kind: "MEMBER",
      material_kind: "PULTRUDED_FRP",
      section_family: "WIDE_FLANGE",
      frame_id: "MEMBER_LOCAL:member-b",
      connected_end: "START",
      elements: [],
      deferred_primitive_ids: [],
    });
    const trianglePoints = [
      { x: "0.75", y: "0", z: "0", unit: "in" as const },
      { x: "2", y: "0", z: "0", unit: "in" as const },
      { x: "0.75", y: "1", z: "0", unit: "in" as const },
    ];
    snapshot.base_connection.primitives = [
      ...snapshot.base_connection.primitives.filter(
        (value) => value.owner_id !== snapshot.connected_member_profile.member_id,
      ),
      {
        ...structuredClone(template),
        id: "tee-brace:LEG_Y:TRIMMED_SOLID",
        label: "Fabricated angle leg Y",
        kind: "TRIANGLE_MESH",
        owner_id: snapshot.connected_member_profile.member_id,
        physical_element_id: "LEG_Y",
        material_region_id: "LEG_Y",
        center: null,
        x_axis: null,
        y_axis: null,
        z_axis: null,
        parameters: [],
        points: trianglePoints,
      },
      {
        ...structuredClone(template),
        id: "support-trimmed-solid",
        label: "Support fabricated solid",
        kind: "TRIANGLE_MESH",
        owner_id: "member-b",
        center: null,
        x_axis: null,
        y_axis: null,
        z_axis: null,
        parameters: [],
        points: trianglePoints,
      },
      {
        ...structuredClone(template),
        id: "connector-trimmed-solid",
        label: "Connector fabricated solid",
        kind: "TRIANGLE_MESH",
        owner_id: "tee-connector",
        center: null,
        x_axis: null,
        y_axis: null,
        z_axis: null,
        parameters: [],
        points: trianglePoints,
      },
      {
        ...structuredClone(template),
        id: "unregistered-trimmed-solid",
        label: "Unregistered fabricated solid",
        kind: "TRIANGLE_MESH",
        owner_id: "unregistered-owner",
        center: null,
        x_axis: null,
        y_axis: null,
        z_axis: null,
        parameters: [],
        points: trianglePoints,
      },
    ];

    const model = buildTeeSceneModel(snapshot);

    expect(model.boxes.some(
      (value) => value.ownerId === snapshot.connected_member_profile.member_id,
    )).toBe(false);
    expect(model.meshes).toEqual(expect.arrayContaining([
      expect.objectContaining({
        id: "tee-brace:LEG_Y:TRIMMED_SOLID",
        ownerId: snapshot.connected_member_profile.member_id,
        ownerRole: "BRACE",
        elementId: "LEG_Y",
        points: [
          { x: 0.75, y: 0, z: 0 },
          { x: 2, y: 0, z: 0 },
          { x: 0.75, y: 1, z: 0 },
        ],
      }),
      expect.objectContaining({
        id: "support-trimmed-solid",
        ownerLabel: "FRP W column",
        ownerRole: "COLUMN",
      }),
      expect.objectContaining({
        id: "connector-trimmed-solid",
        ownerLabel: "Pultruded FRP Tee connector",
        ownerRole: "OTHER",
      }),
      expect.objectContaining({
        id: "unregistered-trimmed-solid",
        ownerLabel: "unregistered-owner",
        ownerRole: "OTHER",
      }),
    ]));
    expect(model.boundsRadius).toBeGreaterThan(0);
  });

  it("renders one real flange/stem solid and both independent solid bolt groups", () => {
    const snapshot = teeVisualizationFixture();
    const model = buildTeeSceneModel(snapshot);

    expect(
      model.boxes
        .filter((box) => box.ownerId === "tee-connector")
        .map((box) => box.elementId),
    ).toEqual(expect.arrayContaining(["FLANGE", "STEM"]));
    const bolts = model.cylinders.filter((value) => value.kind === "BOLT");
    expect(bolts).toHaveLength(8);
    expect(bolts.map((value) => value.ownerBoltId)).toEqual(
      expect.arrayContaining(["A_B_R1_L1", "A_B_R2_L2", "B_B_R1_L1", "B_B_R2_L2"]),
    );
    expect(bolts.every((value) => value.diameter === 0.5)).toBe(true);
    expect(bolts.filter((value) => value.ownerBoltId.startsWith("A_")).every(
      (value) => value.interfaceId === snapshot.base_connection.interface_id,
    )).toBe(true);
    expect(bolts.filter((value) => value.ownerBoltId.startsWith("B_")).every(
      (value) => value.interfaceId === snapshot.interface_b_connection.interface_id,
    )).toBe(true);
    expect(model.markers.filter((value) => value.kind === "BOLT_CENTER")).toHaveLength(8);
    expect(model.markers.find((value) => value.id === "A_B_R1_L1")?.label).toContain(
      "Brace to Tee Stem",
    );
    expect(model.markers.find((value) => value.id === "B_B_R1_L1")?.label).toContain(
      "Tee Flange to Support",
    );
    expect(model.zones.filter((value) => value.selectedContact).map((value) => value.patchId)).toEqual(
      expect.arrayContaining([
        snapshot.selected_connected_surface_patch_id,
        snapshot.selected_support_surface_id,
      ]),
    );
    expect(model.frames.length).toBeGreaterThan(2);
    expect(model.fitRadius).toBeGreaterThan(1);
  });

  it("preserves backend-authored real profile solids and assigns physical member roles", () => {
    const snapshot = teeVisualizationFixture();
    const primitive = snapshot.base_connection.primitives[0];
    if (primitive === undefined) throw new Error("Profile primitive fixture is required.");
    snapshot.base_connection.components.push(
      {
        id: "tee-brace",
        label: "Pultruded FRP connected brace channel",
        participant_kind: "MEMBER",
        material_kind: "PULTRUDED_FRP",
        section_family: "CHANNEL",
        frame_id: "MEMBER_LOCAL:member-a",
        connected_end: "START",
        elements: [],
        deferred_primitive_ids: [],
      },
      {
        id: "tee-support",
        label: "Pultruded FRP W column",
        participant_kind: "MEMBER",
        material_kind: "PULTRUDED_FRP",
        section_family: "WIDE_FLANGE",
        frame_id: "MEMBER_LOCAL:member-b",
        connected_end: "START",
        elements: [],
        deferred_primitive_ids: [],
      },
    );
    snapshot.base_connection.primitives.push(
      {
        ...structuredClone(primitive),
        id: "tee-brace:CHANNEL_WEB",
        owner_id: "tee-brace",
        physical_element_id: "WEB",
        material_region_id: "WEB",
      },
      {
        ...structuredClone(primitive),
        id: "tee-brace:CHANNEL_FLANGE_POS",
        owner_id: "tee-brace",
        physical_element_id: "FLANGE_POSITIVE",
        material_region_id: "FLANGE_POSITIVE",
      },
      {
        ...structuredClone(primitive),
        id: "tee-support:TOP_FLANGE",
        owner_id: "tee-support",
        physical_element_id: "TOP_FLANGE",
        material_region_id: "TOP_FLANGE",
      },
    );
    snapshot.interface_zones = snapshot.interface_zones.map((zone) =>
      zone.patch_id === snapshot.selected_support_surface_id
        ? { ...zone, participant_id: "tee-support" }
        : zone,
    );
    const model = buildTeeSceneModel(snapshot);

    expect(model.boxes.filter((value) => value.ownerId === "tee-brace")).toEqual([
      expect.objectContaining({ id: "tee-brace:CHANNEL_WEB", ownerRole: "BRACE" }),
      expect.objectContaining({ id: "tee-brace:CHANNEL_FLANGE_POS", ownerRole: "BRACE" }),
    ]);
    expect(model.boxes.find((value) => value.id === "tee-support:TOP_FLANGE")).toMatchObject({
      ownerRole: "COLUMN",
    });
  });

  it.each([
    ["ANGLE", ["LEG_Y", "LEG_Z"]],
    ["CHANNEL", ["WEB", "FLANGE_POSITIVE", "FLANGE_NEGATIVE"]],
    ["WIDE_FLANGE_I", ["WEB", "FLANGE_POSITIVE", "FLANGE_NEGATIVE"]],
    ["RECTANGULAR_HOLLOW_SECTION", ["WEB_Y_POSITIVE", "WEB_Y_NEGATIVE", "WEB_Z_POSITIVE", "WEB_Z_NEGATIVE"]],
    ["FLAT_PLATE", ["PLATE"]],
  ] as const)("passes through every backend %s profile solid", (family, elements) => {
    const snapshot = teeVisualizationFixture();
    const primitive = snapshot.base_connection.primitives[0];
    if (primitive === undefined) throw new Error("Profile primitive fixture is required.");
    snapshot.connected_member_profile.profile_family = family;
    snapshot.base_connection.components.push({
      id: "tee-brace",
      label: `Pultruded FRP connected brace ${family}`,
      participant_kind: "MEMBER",
      material_kind: "PULTRUDED_FRP",
      section_family: family,
      frame_id: "MEMBER_LOCAL:member-a",
      connected_end: "START",
      elements: [],
      deferred_primitive_ids: [],
    });
    snapshot.base_connection.primitives.push(...elements.map((element) => ({
      ...structuredClone(primitive),
      id: `tee-brace:${element}`,
      owner_id: "tee-brace",
      physical_element_id: element,
      material_region_id: element,
    })));

    const model = buildTeeSceneModel(snapshot);

    expect(model.boxes.filter((value) => value.ownerId === "tee-brace").map(
      (value) => value.elementId,
    )).toEqual(elements);
    expect(model.boxes.filter((value) => value.ownerId === "tee-brace").every(
      (value) => value.ownerRole === "BRACE",
    )).toBe(true);
  });

  it("retains fallback identity for a backend bolt outside the friendly naming pattern", () => {
    const snapshot = teeVisualizationFixture();
    const first = snapshot.interface_a_bolts[0];
    if (first === undefined) throw new Error("Interface A bolt fixture is required.");
    first.bolt_location_id = "CUSTOM-BOLT";
    const model = buildTeeSceneModel(snapshot);
    expect(model.markers.find((value) => value.id === "CUSTOM-BOLT")?.label).toContain(
      "Tee interface",
    );
    expect(
      model.cylinders.find((value) => value.ownerBoltId === "CUSTOM-BOLT")?.rowId,
    ).toBeNull();
  });

  it("reuses complete solid fastener presentation for both independent Tee interfaces", () => {
    const snapshot = teeVisualizationFixture();
    snapshot.interface_a_bolts = snapshot.interface_a_bolts.slice(0, 2);
    snapshot.interface_a_bolts.forEach((bolt) => { bolt.bolt_diameter = "0.75"; });
    snapshot.interface_b_bolts.forEach((bolt) => { bolt.bolt_diameter = "0.625"; });
    const model = buildTeeSceneModel(snapshot);
    const presentations = buildFastenerPresentations(model.cylinders);

    expect(model.cylinders.filter((value) => value.kind === "BOLT")).toHaveLength(6);
    expect(presentations).toHaveLength(6);
    expect(new Set(presentations.map((value) => value.shank.interfaceId))).toEqual(
      new Set(["interface-1", "TEE_INTERFACE_B_FLANGE_TO_SUPPORT"]),
    );
    expect(new Set(presentations.map((value) => value.shank.diameter))).toEqual(
      new Set([0.75, 0.625]),
    );
    for (const presentation of presentations) {
      const diameter = presentation.shank.diameter;
      const headLength = Math.hypot(
        presentation.head.end.x - presentation.head.start.x,
        presentation.head.end.y - presentation.head.start.y,
        presentation.head.end.z - presentation.head.start.z,
      );
      const nutLength = Math.hypot(
        presentation.nut.end.x - presentation.nut.start.x,
        presentation.nut.end.y - presentation.nut.start.y,
        presentation.nut.end.z - presentation.nut.start.z,
      );
      expect(presentation.head.acrossFlats).toBe(
        diameter * SCHEMATIC_HEAD_ACROSS_FLATS_RATIO,
      );
      expect(headLength).toBeCloseTo(diameter * SCHEMATIC_HEAD_HEIGHT_RATIO, 12);
      expect(presentation.nut.acrossFlats).toBe(
        diameter * SCHEMATIC_NUT_ACROSS_FLATS_RATIO,
      );
      expect(nutLength).toBeCloseTo(diameter * SCHEMATIC_NUT_THICKNESS_RATIO, 12);
      const axis = {
        x: presentation.shank.end.x - presentation.shank.start.x,
        y: presentation.shank.end.y - presentation.shank.start.y,
        z: presentation.shank.end.z - presentation.shank.start.z,
      };
      const headSide = (
        (presentation.head.end.x - presentation.shank.start.x) * axis.x
        + (presentation.head.end.y - presentation.shank.start.y) * axis.y
        + (presentation.head.end.z - presentation.shank.start.z) * axis.z
      );
      const nutSide = (
        (presentation.nut.start.x - presentation.shank.end.x) * axis.x
        + (presentation.nut.start.y - presentation.shank.end.y) * axis.y
        + (presentation.nut.start.z - presentation.shank.end.z) * axis.z
      );
      expect(headSide).toBeLessThanOrEqual(0);
      expect(nutSide).toBeGreaterThanOrEqual(0);
      expect(presentation.washers).toEqual(
        model.cylinders.filter((value) => (
          value.kind === "WASHER" && value.ownerBoltId === presentation.ownerBoltId
        )),
      );
    }
  });

  it("fails closed when Interface A has no authoritative bolt placement", () => {
    const snapshot = teeVisualizationFixture();
    snapshot.interface_a_bolts = [];
    expect(() => buildTeeSceneModel(snapshot)).toThrow(
      "Tee visualization lacks Interface A bolt placements.",
    );
  });
});
